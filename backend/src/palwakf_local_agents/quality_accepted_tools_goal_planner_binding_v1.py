from __future__ import annotations

"""Quality-gated tool selection binding for the Goal Planner.

This module is advisory only. It reads local quality evidence and returns
selection decisions. It never executes tools, models, shell commands, Git,
or network calls, and it does not persist planner decisions.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import re

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

API_PREFIX = "/api/v1/operational-core/planner-tool-selection"
CONTRACT_VERSION = "1.1.0"
BINDING_ID = "QUALITY_ACCEPTED_TOOLS_GOAL_PLANNER_SELECTION_BINDING_V1"

QUALITY_TO_PLANNER = {
    "QUALITY_ACCEPTED": "SELECTABLE",
    "PASS_WITH_LIMITATIONS": "SELECTABLE_WITH_LIMITATIONS",
    "HUMAN_REVIEW_REQUIRED": "HUMAN_REVIEW_REQUIRED",
    "UNASSESSED": "BLOCKED_UNASSESSED",
    "QUALITY_FAILED": "BLOCKED_QUALITY_FAILED",
    "QUARANTINED": "FORBIDDEN_QUARANTINED",
    "REVALIDATION_REQUIRED": "BLOCKED_REVALIDATION_REQUIRED",
}

TOOL_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "tree-sitter": ("code_parse", "code_index", "symbols", "dependencies", "syntax_tree"),
    "opentelemetry": ("local_telemetry", "tracing", "metrics", "observability"),
    "semgrep": ("static_analysis", "security_scan", "code_quality", "pattern_scan"),
    "gitleaks": ("secret_scan", "credential_detection", "security_scan"),
    "trivy": ("dependency_vulnerability_scan", "container_scan", "security_scan"),
    "temporal": ("workflow_orchestration", "durable_workflow"),
    "native-code-index": ("code_index", "symbols", "dependencies"),
    "local-telemetry": ("local_telemetry", "tracing", "metrics"),
}

ALIASES = {
    "tree_sitter": "tree-sitter", "treesitter": "tree-sitter",
    "open_telemetry": "opentelemetry", "otel": "opentelemetry",
    "native_code_index": "native-code-index",
    "native_code_index_contract": "native-code-index",
    "local_telemetry": "local-telemetry",
    "local_telemetry_contract": "local-telemetry",
}

SENSITIVE_KEY_PARTS = ("path", "root", "sha", "hash", "secret", "token", "password", "command", "stdout", "stderr")

class PlanStep(BaseModel):
    step_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    required_capabilities: list[str] = Field(default_factory=list, max_length=20)
    candidate_tool_ids: list[str] = Field(default_factory=list, max_length=30)

class PlannerEvaluationRequest(BaseModel):
    goal_id: str = Field(min_length=1, max_length=160)
    plan_version: str = Field(default="draft", max_length=80)
    steps: list[PlanStep] = Field(min_length=1, max_length=50)
    allow_limited_candidates: bool = False
    human_approval_reference: str | None = Field(default=None, max_length=200)

@dataclass(frozen=True)
class ToolDecision:
    tool_id: str
    quality_state: str
    planner_state: str
    capabilities: tuple[str, ...]
    score: float | None
    limitations: tuple[str, ...]
    reasons: tuple[str, ...]
    baseline_present: bool
    revalidation_required: bool
    baseline_id: str | None
    suite_id: str | None
    quality_run_id: str | None
    last_validation: str | None
    tool_version: str | None
    fixture_version: str | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _source_root() -> Path:
    configured = os.getenv("PALWAKF_LOCAL_AGENTS_SOURCE_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[3]


def _runtime_root() -> Path:
    configured = os.getenv("PALWAKF_TOOL_QUALITY_RUNTIME_ROOT")
    if configured:
        return Path(configured).resolve()
    return _source_root() / "runtime_state" / "operational_core_v1" / "tool_quality_lab"


def _safe_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ("items", "scorecards", "baselines", "quarantines", "runs", "tools"):
            nested = value.get(key)
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]
            if isinstance(nested, dict):
                rows: list[dict[str, Any]] = []
                for nested_key, item in nested.items():
                    if not isinstance(item, dict):
                        continue
                    row = dict(item)
                    row.setdefault("tool_id", nested_key)
                    rows.append(row)
                return rows
        # keyed-by-tool maps without wrapper metadata
        out: list[dict[str, Any]] = []
        for key, item in value.items():
            if key in {"schema_version", "version", "generated_at", "updated_at"}:
                continue
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("tool_id", key)
                out.append(row)
        return out
    return []


def _norm_tool_id(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("-")
    return ALIASES.get(raw, raw)


def _first(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return value
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quality_state(row: dict[str, Any]) -> str:
    raw = str(_first(row, ("quality_result", "quality_state", "state", "status", "result")) or "UNASSESSED").upper()
    aliases = {
        "ACCEPTED": "QUALITY_ACCEPTED", "PASS": "QUALITY_ACCEPTED",
        "LIMITED": "PASS_WITH_LIMITATIONS", "PASS_LIMITED": "PASS_WITH_LIMITATIONS",
        "REVIEW": "HUMAN_REVIEW_REQUIRED", "FAILED": "QUALITY_FAILED",
        "QUARANTINE": "QUARANTINED", "REVALIDATE": "REVALIDATION_REQUIRED",
        "READINESS_HOLD": "UNASSESSED", "DEFERRED": "UNASSESSED", "MISSING_NOT_FAILED": "UNASSESSED",
    }
    return aliases.get(raw, raw if raw in QUALITY_TO_PLANNER else "UNASSESSED")


def _fingerprint(row: dict[str, Any]) -> str | None:
    explicit = _first(row, ("fingerprint", "quality_fingerprint", "artifact_fingerprint", "normalized_result_hash", "result_hash"))
    if explicit:
        return str(explicit)
    parts = [_first(row, keys) for keys in (
        ("version", "tool_version"), ("adapter_version", "adapter_id"),
        ("adapter_sha256", "adapter_hash"), ("fixture_sha256", "fixture_hash"),
        ("suite_version", "benchmark_version"),
    )]
    if not any(x is not None for x in parts):
        return None
    return hashlib.sha256("|".join(str(x or "") for x in parts).encode("utf-8")).hexdigest()


def _latest_by_tool(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        tool_id = _norm_tool_id(_first(row, ("tool_id", "tool", "adapter_id", "name", "subject_id")))
        if tool_id:
            out[tool_id] = row
    return out


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
                continue
            clean[key] = _redact(item)
        return clean
    if isinstance(value, list):
        return [_redact(x) for x in value]
    return value


def load_quality_snapshot() -> dict[str, Any]:
    root = _runtime_root()
    raw_scorecards = _records(_safe_json(root / "scorecards.json", []))
    raw_baselines = _records(_safe_json(root / "quality_baselines.json", []))
    raw_quarantines = _records(_safe_json(root / "quarantines.json", []))

    scorecards = _latest_by_tool(raw_scorecards)
    baselines = _latest_by_tool(raw_baselines)
    quarantines = _latest_by_tool(raw_quarantines)

    canonical_tools = set(TOOL_CAPABILITIES)
    ignored_ids = sorted(
        {
            tool_id
            for tool_id in set(scorecards) | set(baselines) | set(quarantines)
            if tool_id not in canonical_tools
        }
    )

    decisions: dict[str, ToolDecision] = {}
    for tool_id in sorted(canonical_tools):
        score = scorecards.get(tool_id, {})
        baseline = baselines.get(tool_id, {})
        quarantine = quarantines.get(tool_id, {})
        state = _quality_state(score)
        reasons: list[str] = []

        limitations_raw = _first(score, ("limitations", "warnings", "constraints")) or []
        if isinstance(limitations_raw, str):
            limitations = (limitations_raw[:240],)
        elif isinstance(limitations_raw, list):
            limitations = tuple(str(x)[:240] for x in limitations_raw)
        else:
            limitations = ()

        quarantine_active = bool(quarantine) and str(
            quarantine.get("active", True)
        ).lower() not in ("false", "0", "no")
        if quarantine_active:
            state = "QUARANTINED"
            reasons.append("ACTIVE_QUARANTINE_WINS")

        baseline_present = bool(baseline)
        revalidation = False
        current_fp = _fingerprint(score)
        baseline_fp = _fingerprint(baseline)

        if state in ("QUALITY_ACCEPTED", "PASS_WITH_LIMITATIONS"):
            if not baseline_present:
                state = "REVALIDATION_REQUIRED"
                revalidation = True
                reasons.append("QUALITY_BASELINE_MISSING")
            elif not current_fp or not baseline_fp:
                state = "REVALIDATION_REQUIRED"
                revalidation = True
                reasons.append("QUALITY_FINGERPRINT_MISSING")
            elif current_fp != baseline_fp:
                state = "REVALIDATION_REQUIRED"
                revalidation = True
                reasons.append("TOOL_VERSION_ADAPTER_OR_FIXTURE_CHANGED")

        if not score:
            reasons.append("NO_QUALITY_SCORECARD")
        if state == "UNASSESSED":
            reasons.append("QUALITY_NOT_ASSESSED")

        decisions[tool_id] = ToolDecision(
            tool_id=tool_id,
            quality_state=state,
            planner_state=QUALITY_TO_PLANNER[state],
            capabilities=TOOL_CAPABILITIES.get(tool_id, ()),
            score=_float_or_none(_first(score, ("score", "quality_score", "total_score"))),
            limitations=limitations,
            reasons=tuple(reasons),
            baseline_present=baseline_present,
            revalidation_required=revalidation,
            baseline_id=str(_first(baseline, ("baseline_id", "id"))) if baseline else None,
            suite_id=str(_first(score, ("suite_id", "benchmark_id"))) if score else None,
            quality_run_id=str(_first(score, ("last_run_id", "run_id"))) if score else None,
            last_validation=str(
                _first(score, ("updated_at", "completed_at", "validated_at"))
                or _first(baseline, ("accepted_at", "updated_at"))
                or ""
            ) or None,
            tool_version=str(
                _first(baseline, ("tool_version", "version"))
                or _first(score, ("tool_version", "version"))
                or ""
            ) or None,
            fixture_version=str(
                _first(baseline, ("fixture_version", "benchmark_version"))
                or _first(score, ("fixture_version", "benchmark_version"))
                or ""
            ) or None,
        )

    selectable_count = sum(
        1
        for decision in decisions.values()
        if decision.planner_state in ("SELECTABLE", "SELECTABLE_WITH_LIMITATIONS")
    )
    return {
        "runtime_available": root.exists(),
        "tool_count": len(decisions),
        "selectable_count": selectable_count,
        "reconciliation": {
            "contract_version": "1.1.0",
            "canonical_tool_count": len(canonical_tools),
            "scorecard_records_read": len(raw_scorecards),
            "baseline_records_read": len(raw_baselines),
            "quarantine_records_read": len(raw_quarantines),
            "ignored_noncanonical_ids": ignored_ids,
            "automatic_quality_acceptance": False,
            "tool_execution_performed": False,
        },
        "tools": {k: _redact(asdict(v)) for k, v in decisions.items()},
    }


def _candidate_ids(step: PlanStep, snapshot: dict[str, Any]) -> list[str]:
    explicit = [_norm_tool_id(x) for x in step.candidate_tool_ids if _norm_tool_id(x)]
    if explicit:
        return list(dict.fromkeys(explicit))
    required = {str(x).strip().lower() for x in step.required_capabilities if str(x).strip()}
    if not required:
        return []
    matches: list[str] = []
    for tool_id, decision in snapshot["tools"].items():
        caps = {str(x).lower() for x in decision.get("capabilities", [])}
        if required.issubset(caps):
            matches.append(tool_id)
    return matches


def evaluate_plan(req: PlannerEvaluationRequest) -> dict[str, Any]:
    snapshot = load_quality_snapshot()
    evaluated_steps: list[dict[str, Any]] = []
    plan_blocked = False
    limited_approval = bool(req.allow_limited_candidates and req.human_approval_reference)

    for step in req.steps:
        candidates = _candidate_ids(step, snapshot)
        rows: list[dict[str, Any]] = []
        for tool_id in candidates:
            decision = snapshot["tools"].get(tool_id)
            if decision is None:
                decision = _redact(asdict(ToolDecision(
                    tool_id=tool_id, quality_state="UNASSESSED", planner_state="BLOCKED_UNASSESSED",
                    capabilities=TOOL_CAPABILITIES.get(tool_id, ()), score=None, limitations=(),
                    reasons=("TOOL_NOT_IN_QUALITY_SNAPSHOT",), baseline_present=False,
                    revalidation_required=False, baseline_id=None, suite_id=None,
                    quality_run_id=None, last_validation=None, tool_version=None,
                    fixture_version=None,
                )))
            rows.append(decision)

        selectable = [x for x in rows if x["planner_state"] == "SELECTABLE"]
        limited = [x for x in rows if x["planner_state"] == "SELECTABLE_WITH_LIMITATIONS"]
        selected: dict[str, Any] | None = None
        selection_basis = "NONE"
        if selectable:
            selectable.sort(key=lambda x: (x.get("score") is not None, x.get("score") or -1), reverse=True)
            selected = selectable[0]
            selection_basis = "QUALITY_ACCEPTED_HIGHEST_SCORE"
        elif limited and limited_approval:
            limited.sort(key=lambda x: (x.get("score") is not None, x.get("score") or -1), reverse=True)
            selected = limited[0]
            selection_basis = "LIMITED_WITH_EXPLICIT_HUMAN_APPROVAL_REFERENCE"
        else:
            plan_blocked = True

        evaluated_steps.append({
            "step_id": step.step_id,
            "title": step.title,
            "required_capabilities": step.required_capabilities,
            "selected_tool": selected,
            "selection_basis": selection_basis,
            "human_review_required": bool(limited and not selected),
            "candidate_decisions": rows,
            "step_state": "PLANNABLE" if selected else "BLOCKED_NO_ELIGIBLE_TOOL",
        })

    return {
        "binding_id": BINDING_ID,
        "contract_version": CONTRACT_VERSION,
        "generated_at": _utc_now(),
        "goal_id": req.goal_id,
        "plan_version": req.plan_version,
        "plan_state": "BLOCKED" if plan_blocked else "QUALITY_GATED_PLAN_READY_FOR_HUMAN_REVIEW",
        "execution_performed": False,
        "state_persisted": False,
        "human_authority_required": True,
        "steps": evaluated_steps,
    }


def create_router() -> APIRouter:
    router = APIRouter(prefix=API_PREFIX, tags=["planner-tool-selection"])

    @router.get("/health")
    def health() -> dict[str, Any]:
        snapshot = load_quality_snapshot()
        return {
            "status": "ok",
            "binding_id": BINDING_ID,
            "contract_version": CONTRACT_VERSION,
            "quality_runtime_available": snapshot["runtime_available"],
            "tool_count": snapshot["tool_count"],
            "selectable_count": snapshot["selectable_count"],
            "reconciliation_contract": snapshot["reconciliation"]["contract_version"],
            "execution": "BLOCKED_BY_CONTRACT",
            "persistence": "NONE",
            "network": "NONE",
        }

    @router.get("/policy")
    def policy() -> dict[str, Any]:
        return {
            "quality_to_planner": QUALITY_TO_PLANNER,
            "rules": [
                "QUALITY_ACCEPTED tools are selectable.",
                "PASS_WITH_LIMITATIONS requires an explicit human approval reference.",
                "HUMAN_REVIEW_REQUIRED is not auto-selected.",
                "UNASSESSED and QUALITY_FAILED are blocked.",
                "QUARANTINED is forbidden.",
                "Version, adapter, or fixture drift requires revalidation.",
            ],
            "forbidden": ["MODEL_INFERENCE", "SHELL", "GIT", "TOOL_EXECUTION", "SELF_APPLY", "NETWORK"],
        }

    @router.get("/tools")
    def tools() -> dict[str, Any]:
        return load_quality_snapshot()

    @router.post("/evaluate")
    def evaluate(req: PlannerEvaluationRequest) -> dict[str, Any]:
        if req.allow_limited_candidates and not req.human_approval_reference:
            raise HTTPException(status_code=422, detail="HUMAN_APPROVAL_REFERENCE_REQUIRED_FOR_LIMITED_CANDIDATES")
        return evaluate_plan(req)

    return router


def install_quality_planner_binding(app: FastAPI) -> None:
    state = getattr(app, "state", None)
    if state is not None and getattr(state, "quality_planner_binding_v1_installed", False):
        return
    app.include_router(create_router())
    if state is not None:
        state.quality_planner_binding_v1_installed = True
