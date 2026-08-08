from __future__ import annotations

import difflib
import hashlib
import http.client
import json
import os
import re
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["full-stack-operational-waves-3-to-8-v1"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "full_stack_waves_3_8"
MODELS_FILE = RUNTIME_ROOT / "model_registry.json"
CONTEXTS_FILE = RUNTIME_ROOT / "context_packs.json"
PLANS_FILE = RUNTIME_ROOT / "plans.json"
PROPOSALS_FILE = RUNTIME_ROOT / "proposals.json"
IMPLEMENTATIONS_FILE = RUNTIME_ROOT / "implementations.json"
PROJECT_STATE_FILE = RUNTIME_ROOT / "project_state.json"
READINESS_FILE = RUNTIME_ROOT / "readiness.json"
REVIEWS_FILE = RUNTIME_ROOT / "reviews.jsonl"
EVIDENCE_FILE = RUNTIME_ROOT / "evidence.jsonl"
BACKUPS_ROOT = RUNTIME_ROOT / "implementation_backups"

QUALITY_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "tool_quality_lab"
QUALITY_BASELINES_FILE = QUALITY_ROOT / "quality_baselines.json"

_LOCK = threading.RLock()
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MAX_CONTEXT_FILES = 120
MAX_CONTEXT_BYTES = 180_000
MAX_TARGET_FILES = 5
MAX_TARGET_FILE_BYTES = 220_000
MAX_PROPOSAL_BYTES = 700_000
PROMPT_VERSION = "LOCAL_PLANNING_AND_CHANGE_PROPOSAL_V1"
RUNTIME_VERSION = "FULL_STACK_WAVES_3_TO_8_V1"

MODEL_DEFAULTS = {
    "qwen2.5:3b": {"label": "Qwen 2.5 3B", "purpose": "planning_and_change_proposal"},
    "llama3.2:3b": {"label": "Llama 3.2 3B", "purpose": "planning_and_change_proposal"},
}

ALLOWED_TOOLS = {
    "project_summary", "route_index", "component_index", "symbol_index",
    "docs_index", "file_metadata", "project_reader", "route_reader",
    "semgrep", "gitleaks",
}

TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".dart", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".html", ".css", ".scss", ".sql",
}
EXCLUDED_PARTS = {
    ".git", ".svn", ".hg", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".dart_tool", "runtime_state",
}
BLOCKED_FILENAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".crt", ".cer"}

PLAN_SYSTEM_PROMPT = """
You are the planning component of a governed local engineering agent.
Return one JSON object only. Do not use Markdown.
You may plan and recommend quality-accepted tools.
You must not instruct shell, Git, network access, self-application, deletion,
credential access, source mutation, or autonomous execution.
Required keys:
goal_summary, assumptions, constraints, recommended_steps, risks,
validation_plan, human_decisions_required.
recommended_steps must be a list of objects with:
step_id, title, description, recommended_tools, requires_human_decision.
""".strip()

PROPOSAL_SYSTEM_PROMPT = """
You are a governed local code-change proposal component.
Return one JSON object only. Do not use Markdown.
Required key: changes.
changes must be a list of objects with path, new_content, reason.
Only use the exact target paths provided. Do not add files, delete files,
use shell, Git, network access, or self-apply. Preserve unrelated content.
""".strip()


class ContextRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=6000)
    scope_relative: str = Field(default=".", max_length=500)


class ModelApprovalRequest(BaseModel):
    approval_reference: str = Field(min_length=3, max_length=300)
    approved_by: str = Field(min_length=2, max_length=120)


class PlanGenerateRequest(BaseModel):
    context_pack_id: str
    model_id: str


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|RETURN|REJECT)$")
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=3000)


class ProposalGenerateRequest(BaseModel):
    plan_id: str
    model_id: str
    target_files: list[str] = Field(min_length=1, max_length=MAX_TARGET_FILES)


class ImplementationPrepareRequest(BaseModel):
    proposal_id: str
    approved_by: str = Field(min_length=2, max_length=120)
    approval_reference: str = Field(min_length=3, max_length=300)


class ApplyRequest(BaseModel):
    apply_token: str = Field(min_length=10, max_length=200)


class ImplementationReviewRequest(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|ROLLBACK)$")
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=3000)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def _ensure_state() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    BACKUPS_ROOT.mkdir(parents=True, exist_ok=True)
    if not MODELS_FILE.exists():
        _atomic_write_json(
            MODELS_FILE,
            {
                "schema_version": "1.0.0",
                "models": {
                    model_id: {
                        "model_id": model_id,
                        **meta,
                        "state": "REGISTERED",
                        "digest": None,
                        "approved_digest": None,
                        "approval_reference": None,
                        "approved_by": None,
                        "last_probe_at": None,
                    }
                    for model_id, meta in MODEL_DEFAULTS.items()
                },
            },
        )
    for path, key in [
        (CONTEXTS_FILE, "context_packs"),
        (PLANS_FILE, "plans"),
        (PROPOSALS_FILE, "proposals"),
        (IMPLEMENTATIONS_FILE, "implementations"),
    ]:
        if not path.exists():
            _atomic_write_json(path, {"schema_version": "1.0.0", key: {}})
    if not PROJECT_STATE_FILE.exists():
        _atomic_write_json(
            PROJECT_STATE_FILE,
            {
                "schema_version": "1.0.0",
                "revision": 0,
                "status": "INITIALIZING",
                "progress_percent": 0,
                "risks": [],
                "updated_at": _utc_now(),
            },
        )
    if not READINESS_FILE.exists():
        _atomic_write_json(
            READINESS_FILE,
            {
                "schema_version": "1.0.0",
                "status": "NOT_ASSESSED",
                "production_approval": "NOT_APPROVED",
                "gates": [],
                "updated_at": _utc_now(),
            },
        )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _sha256_json(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _event(event_type: str, entity_id: str, details: dict[str, Any]) -> None:
    _append_jsonl(
        EVIDENCE_FILE,
        {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "entity_id": entity_id,
            "occurred_at": _utc_now(),
            "details": details,
        },
    )


def _resolve_relative(relative: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError("ABSOLUTE_PATH_BLOCKED")
    resolved = (PROJECT_ROOT / candidate).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("WORKSPACE_ESCAPE_BLOCKED") from exc
    if must_exist and not resolved.exists():
        raise ValueError("PATH_NOT_FOUND")
    return resolved


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _blocked_file(path: Path) -> bool:
    if path.name.lower() in BLOCKED_FILENAMES:
        return True
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return True
    return any(part.startswith(".") or part in EXCLUDED_PARTS for part in path.relative_to(PROJECT_ROOT).parts)


def _redact(text: str) -> tuple[str, bool]:
    original = text
    for value in {str(PROJECT_ROOT), str(PROJECT_ROOT).replace("\\", "/")}:
        text = text.replace(value, "<WORKSPACE>")
    patterns = [
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "<REDACTED_PRIVATE_KEY>"),
        (r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*['\"]?[^'\"\s,;]+", r"\1=<REDACTED>"),
        (r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{8,}\b", "<REDACTED_TOKEN>"),
        (r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s\"']+", "<REDACTED_CONNECTION_STRING>"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return text, text != original


def _ollama_request(method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 90) -> dict[str, Any]:
    if path not in {"/api/tags", "/api/generate"}:
        raise ValueError("LOCAL_MODEL_PATH_BLOCKED")
    connection = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(4_000_000)
    finally:
        connection.close()
    if response.status < 200 or response.status >= 300:
        raise RuntimeError(f"LOCAL_MODEL_HTTP_{response.status}")
    return json.loads(raw.decode("utf-8"))


def _probe_models() -> dict[str, Any]:
    _ensure_state()
    response = _ollama_request("GET", "/api/tags", timeout=10)
    available = {}
    for item in response.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            available[name] = item
    state = _read_json(MODELS_FILE, {"schema_version": "1.0.0", "models": {}})
    for model_id, record in state["models"].items():
        item = available.get(model_id)
        digest = item.get("digest") if item else None
        record["digest"] = digest
        record["last_probe_at"] = _utc_now()
        if not item:
            record["state"] = "REGISTERED"
        elif record.get("approved_digest") == digest and digest:
            record["state"] = "PLANNING_APPROVED"
        else:
            record["state"] = "AVAILABLE"
    _atomic_write_json(MODELS_FILE, state)
    _event("LOCAL_MODELS_PROBED", "model-registry", {"available_count": len(available)})
    return state


def _approve_model(model_id: str, request: ModelApprovalRequest) -> dict[str, Any]:
    _ensure_state()
    state = _read_json(MODELS_FILE, {"schema_version": "1.0.0", "models": {}})
    model = state["models"].get(model_id)
    if not model:
        raise ValueError("UNKNOWN_MODEL_ID")
    if model.get("state") != "AVAILABLE" or not model.get("digest"):
        raise ValueError("MODEL_NOT_AVAILABLE_FOR_APPROVAL")
    model["state"] = "PLANNING_APPROVED"
    model["approved_digest"] = model["digest"]
    model["approval_reference"] = request.approval_reference
    model["approved_by"] = request.approved_by
    model["approved_at"] = _utc_now()
    _atomic_write_json(MODELS_FILE, state)
    _event("LOCAL_MODEL_APPROVED", model_id, {"digest": model["digest"], "approved_by": request.approved_by})
    return model


def _approved_model(model_id: str) -> dict[str, Any]:
    state = _read_json(MODELS_FILE, {"schema_version": "1.0.0", "models": {}})
    model = state.get("models", {}).get(model_id)
    if not model:
        raise ValueError("UNKNOWN_MODEL_ID")
    if model.get("state") != "PLANNING_APPROVED":
        raise ValueError("MODEL_NOT_PLANNING_APPROVED")
    if not model.get("digest") or model.get("digest") != model.get("approved_digest"):
        raise ValueError("MODEL_DIGEST_REVALIDATION_REQUIRED")
    return model


def _quality_baseline_summary() -> list[dict[str, Any]]:
    data = _read_json(QUALITY_BASELINES_FILE, {"baselines": {}})
    result = []
    for tool_id, baseline in data.get("baselines", {}).items():
        if baseline.get("quality_result") in {"QUALITY_ACCEPTED", "PASS_WITH_LIMITATIONS"}:
            result.append({
                "tool_id": tool_id,
                "quality_result": baseline.get("quality_result"),
                "baseline_id": baseline.get("baseline_id"),
                "limitations": baseline.get("limitations", []),
            })
    return result


def _context_files(scope: Path) -> list[dict[str, Any]]:
    files = []
    total = 0
    candidates = [scope] if scope.is_file() else sorted(scope.rglob("*"))
    for path in candidates:
        if len(files) >= MAX_CONTEXT_FILES or total >= MAX_CONTEXT_BYTES:
            break
        if not path.is_file() or _blocked_file(path):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        size = path.stat().st_size
        if size > 80_000:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        redacted, changed = _redact(content[:12_000])
        encoded = redacted.encode("utf-8")
        if total + len(encoded) > MAX_CONTEXT_BYTES:
            break
        total += len(encoded)
        files.append({
            "path": _relative(path),
            "sha256": _sha256_file(path),
            "size_bytes": size,
            "redaction_applied": changed,
            "excerpt": redacted,
        })
    return files


def _create_context(request: ContextRequest) -> dict[str, Any]:
    scope = _resolve_relative(request.scope_relative)
    files = _context_files(scope)
    context_id = str(uuid.uuid4())
    payload = {
        "context_pack_id": context_id,
        "goal": request.goal,
        "scope_relative": _relative(scope),
        "files": files,
        "quality_accepted_tools": _quality_baseline_summary(),
        "created_at": _utc_now(),
        "redaction_required": True,
        "absolute_paths": "blocked",
    }
    payload["context_sha256"] = _sha256_json({
        "goal": payload["goal"],
        "scope_relative": payload["scope_relative"],
        "files": [{"path": item["path"], "sha256": item["sha256"]} for item in files],
        "quality_accepted_tools": payload["quality_accepted_tools"],
    })
    with _LOCK:
        state = _read_json(CONTEXTS_FILE, {"schema_version": "1.0.0", "context_packs": {}})
        state["context_packs"][context_id] = payload
        _atomic_write_json(CONTEXTS_FILE, state)
    _event("CONTEXT_PACK_CREATED", context_id, {"file_count": len(files), "context_sha256": payload["context_sha256"]})
    return payload


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("MODEL_OUTPUT_JSON_NOT_FOUND")
        return json.loads(stripped[start:end + 1])


def _validate_plan(value: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    required = [
        "goal_summary", "assumptions", "constraints", "recommended_steps",
        "risks", "validation_plan", "human_decisions_required",
    ]
    for key in required:
        if key not in value:
            raise ValueError(f"PLAN_SCHEMA_MISSING_{key}")
    if not isinstance(value["goal_summary"], str):
        raise ValueError("PLAN_SCHEMA_GOAL_SUMMARY_INVALID")
    for key in ["assumptions", "constraints", "risks", "validation_plan", "human_decisions_required"]:
        if not isinstance(value[key], list) or not all(isinstance(item, str) for item in value[key]):
            raise ValueError(f"PLAN_SCHEMA_{key.upper()}_INVALID")
    if not isinstance(value["recommended_steps"], list):
        raise ValueError("PLAN_SCHEMA_RECOMMENDED_STEPS_INVALID")

    warnings = []
    normalized_steps = []
    for index, step in enumerate(value["recommended_steps"], start=1):
        if not isinstance(step, dict):
            raise ValueError("PLAN_STEP_NOT_OBJECT")
        tools = step.get("recommended_tools", [])
        if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
            raise ValueError("PLAN_STEP_TOOLS_INVALID")
        unknown = sorted(set(tools) - ALLOWED_TOOLS)
        if unknown:
            raise ValueError(f"PLAN_UNKNOWN_TOOLS={','.join(unknown)}")
        normalized = {
            "step_id": str(step.get("step_id") or f"S{index}"),
            "title": str(step.get("title") or f"Step {index}"),
            "description": str(step.get("description") or ""),
            "recommended_tools": tools,
            "requires_human_decision": bool(step.get("requires_human_decision", True)),
        }
        action_text = f"{normalized['title']} {normalized['description']}".lower()
        forbidden = [
            r"\bpowershell\b", r"\bcmd\.exe\b", r"\bbash\b", r"\bshell\b",
            r"\bgit\s+(commit|push|checkout|reset|merge)\b",
            r"\bcurl\b", r"\bwget\b", r"\bself[- ]?apply\b",
            r"\bdelete\s+(file|directory|source)\b",
        ]
        if any(re.search(pattern, action_text) for pattern in forbidden):
            raise ValueError("PLAN_FORBIDDEN_EXECUTION_INSTRUCTION")
        normalized_steps.append(normalized)
    value["recommended_steps"] = normalized_steps
    if not normalized_steps:
        warnings.append("Plan contains no recommended steps.")
    return value, warnings


def _generate_model_json(model_id: str, system_prompt: str, user_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    model = _approved_model(model_id)
    prompt = system_prompt + "\n\nINPUT_JSON:\n" + json.dumps(user_payload, ensure_ascii=False)
    started = time.monotonic()
    response = _ollama_request(
        "POST",
        "/api/generate",
        {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 1800},
        },
        timeout=120,
    )
    raw = str(response.get("response") or "")
    parsed = _extract_json(raw)
    meta = {
        "model_id": model_id,
        "model_digest": model["digest"],
        "duration_ms": int((time.monotonic() - started) * 1000),
        "response_sha256": _sha256_text(raw),
        "prompt_version": PROMPT_VERSION,
        "localhost_only": True,
    }
    return parsed, meta


def _generate_plan(request: PlanGenerateRequest) -> dict[str, Any]:
    contexts = _read_json(CONTEXTS_FILE, {"context_packs": {}}).get("context_packs", {})
    context = contexts.get(request.context_pack_id)
    if not context:
        raise ValueError("CONTEXT_PACK_NOT_FOUND")
    payload = {
        "goal": context["goal"],
        "scope_relative": context["scope_relative"],
        "files": [{"path": item["path"], "excerpt": item["excerpt"]} for item in context["files"]],
        "quality_accepted_tools": context["quality_accepted_tools"],
        "constraints": [
            "planning only", "no automatic execution", "no shell", "no Git",
            "no external network", "no source write", "human approval required",
        ],
    }
    model_value, meta = _generate_model_json(request.model_id, PLAN_SYSTEM_PROMPT, payload)
    normalized, warnings = _validate_plan(model_value)
    plan_id = str(uuid.uuid4())
    plan = {
        "plan_id": plan_id,
        "context_pack_id": request.context_pack_id,
        "status": "HUMAN_REVIEW",
        "plan": normalized,
        "warnings": warnings,
        "model": meta,
        "created_at": _utc_now(),
        "review": None,
        "automatic_acceptance": False,
        "tool_execution": "none",
    }
    plan["plan_sha256"] = _sha256_json({"plan": normalized, "context_pack_id": request.context_pack_id, "model_digest": meta["model_digest"]})
    with _LOCK:
        state = _read_json(PLANS_FILE, {"schema_version": "1.0.0", "plans": {}})
        state["plans"][plan_id] = plan
        _atomic_write_json(PLANS_FILE, state)
    _event("LOCAL_PLAN_GENERATED", plan_id, {"plan_sha256": plan["plan_sha256"], "model_id": request.model_id})
    return plan


def _review_entity(path: Path, key: str, entity_id: str, request: ReviewRequest, allowed_status: str) -> dict[str, Any]:
    with _LOCK:
        state = _read_json(path, {"schema_version": "1.0.0", key: {}})
        entity = state[key].get(entity_id)
        if not entity:
            raise ValueError("ENTITY_NOT_FOUND")
        if entity.get("status") != allowed_status:
            raise ValueError("ENTITY_NOT_READY_FOR_REVIEW")
        status_map = {"ACCEPT": "ACCEPTED", "RETURN": "RETURNED", "REJECT": "REJECTED"}
        review = {
            "review_id": str(uuid.uuid4()),
            "entity_id": entity_id,
            "entity_type": key,
            "decision": request.decision,
            "reviewed_by": request.reviewed_by,
            "notes": request.notes,
            "reviewed_at": _utc_now(),
        }
        entity["status"] = status_map[request.decision]
        entity["review"] = review
        _atomic_write_json(path, state)
        _append_jsonl(REVIEWS_FILE, review)
    _event(f"{key.upper()}_REVIEWED", entity_id, {"decision": request.decision, "reviewed_by": request.reviewed_by})
    return entity


def _safe_target(relative: str) -> Path:
    path = _resolve_relative(relative)
    if not path.is_file():
        raise ValueError("TARGET_NOT_FILE")
    if _blocked_file(path):
        raise ValueError("TARGET_FILE_BLOCKED")
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        raise ValueError("TARGET_EXTENSION_BLOCKED")
    if path.stat().st_size > MAX_TARGET_FILE_BYTES:
        raise ValueError("TARGET_FILE_TOO_LARGE")
    return path


def _validate_proposal(value: dict[str, Any], targets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    changes = value.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValueError("PROPOSAL_CHANGES_REQUIRED")
    normalized = []
    total = 0
    seen = set()
    for item in changes:
        if not isinstance(item, dict):
            raise ValueError("PROPOSAL_CHANGE_NOT_OBJECT")
        path = str(item.get("path") or "")
        if path not in targets:
            raise ValueError("PROPOSAL_PATH_NOT_AUTHORIZED")
        if path in seen:
            raise ValueError("PROPOSAL_DUPLICATE_PATH")
        seen.add(path)
        new_content = item.get("new_content")
        if not isinstance(new_content, str):
            raise ValueError("PROPOSAL_NEW_CONTENT_INVALID")
        total += len(new_content.encode("utf-8"))
        if total > MAX_PROPOSAL_BYTES:
            raise ValueError("PROPOSAL_TOO_LARGE")
        reason = str(item.get("reason") or "")
        diff = "".join(
            difflib.unified_diff(
                targets[path]["content"].splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        normalized.append({
            "path": path,
            "preimage_sha256": targets[path]["sha256"],
            "new_content": new_content,
            "postimage_sha256": _sha256_text(new_content),
            "reason": reason,
            "diff": diff[:180_000],
        })
    return normalized


def _generate_proposal(request: ProposalGenerateRequest) -> dict[str, Any]:
    plans = _read_json(PLANS_FILE, {"plans": {}}).get("plans", {})
    plan = plans.get(request.plan_id)
    if not plan:
        raise ValueError("PLAN_NOT_FOUND")
    if plan.get("status") != "ACCEPTED":
        raise ValueError("ACCEPTED_PLAN_REQUIRED")

    targets: dict[str, dict[str, Any]] = {}
    for relative in request.target_files:
        path = _safe_target(relative)
        normalized = _relative(path)
        if normalized in targets:
            raise ValueError("DUPLICATE_TARGET_FILE")
        content = path.read_text(encoding="utf-8", errors="strict")
        targets[normalized] = {
            "content": content,
            "sha256": _sha256_file(path),
        }

    model_payload = {
        "accepted_plan": plan["plan"],
        "targets": [{"path": path, "content": value["content"]} for path, value in targets.items()],
        "constraints": [
            "proposal only", "existing files only", "no source apply", "no shell",
            "no Git", "no network", "preserve unrelated content",
        ],
    }
    model_value, meta = _generate_model_json(request.model_id, PROPOSAL_SYSTEM_PROMPT, model_payload)
    changes = _validate_proposal(model_value, targets)

    proposal_id = str(uuid.uuid4())
    proposal = {
        "proposal_id": proposal_id,
        "plan_id": request.plan_id,
        "status": "HUMAN_REVIEW",
        "changes": changes,
        "model": meta,
        "created_at": _utc_now(),
        "review": None,
        "applied": False,
    }
    proposal["proposal_sha256"] = _sha256_json({
        "plan_id": request.plan_id,
        "changes": [{"path": item["path"], "preimage_sha256": item["preimage_sha256"], "postimage_sha256": item["postimage_sha256"]} for item in changes],
        "model_digest": meta["model_digest"],
    })
    with _LOCK:
        state = _read_json(PROPOSALS_FILE, {"schema_version": "1.0.0", "proposals": {}})
        state["proposals"][proposal_id] = proposal
        _atomic_write_json(PROPOSALS_FILE, state)
    _event("CHANGE_PROPOSAL_GENERATED", proposal_id, {"proposal_sha256": proposal["proposal_sha256"], "change_count": len(changes)})
    return proposal


def _prepare_implementation(request: ImplementationPrepareRequest) -> dict[str, Any]:
    proposals = _read_json(PROPOSALS_FILE, {"proposals": {}}).get("proposals", {})
    proposal = proposals.get(request.proposal_id)
    if not proposal:
        raise ValueError("PROPOSAL_NOT_FOUND")
    if proposal.get("status") != "ACCEPTED":
        raise ValueError("ACCEPTED_PROPOSAL_REQUIRED")
    if proposal.get("applied"):
        raise ValueError("PROPOSAL_ALREADY_APPLIED")

    for change in proposal["changes"]:
        path = _safe_target(change["path"])
        if _sha256_file(path) != change["preimage_sha256"]:
            raise ValueError("PROPOSAL_PREIMAGE_STALE")

    implementation_id = str(uuid.uuid4())
    apply_token = f"APPLY-{uuid.uuid4()}"
    implementation = {
        "implementation_id": implementation_id,
        "proposal_id": request.proposal_id,
        "status": "APPROVED_FOR_APPLY",
        "approved_by": request.approved_by,
        "approval_reference": request.approval_reference,
        "approved_at": _utc_now(),
        "apply_token_sha256": _sha256_text(apply_token),
        "apply_token": apply_token,
        "proposal_sha256": proposal["proposal_sha256"],
        "changes": [
            {
                "path": item["path"],
                "preimage_sha256": item["preimage_sha256"],
                "postimage_sha256": item["postimage_sha256"],
            }
            for item in proposal["changes"]
        ],
        "source_write": "human_approved_only",
        "shell": "none",
        "git": "none",
        "automatic_apply": False,
    }
    implementation["implementation_manifest_sha256"] = _sha256_json({
        "proposal_sha256": proposal["proposal_sha256"],
        "changes": implementation["changes"],
        "approved_by": request.approved_by,
        "approval_reference": request.approval_reference,
    })
    with _LOCK:
        state = _read_json(IMPLEMENTATIONS_FILE, {"schema_version": "1.0.0", "implementations": {}})
        state["implementations"][implementation_id] = implementation
        _atomic_write_json(IMPLEMENTATIONS_FILE, state)
    _event("IMPLEMENTATION_APPROVED", implementation_id, {"proposal_id": request.proposal_id, "approved_by": request.approved_by})
    return implementation


def _apply_implementation(implementation_id: str, request: ApplyRequest) -> dict[str, Any]:
    with _LOCK:
        implementations = _read_json(IMPLEMENTATIONS_FILE, {"schema_version": "1.0.0", "implementations": {}})
        implementation = implementations["implementations"].get(implementation_id)
        if not implementation:
            raise ValueError("IMPLEMENTATION_NOT_FOUND")
        if implementation.get("status") != "APPROVED_FOR_APPLY":
            raise ValueError("IMPLEMENTATION_NOT_READY_FOR_APPLY")
        if _sha256_text(request.apply_token) != implementation["apply_token_sha256"]:
            raise ValueError("APPLY_TOKEN_MISMATCH")

        proposals = _read_json(PROPOSALS_FILE, {"schema_version": "1.0.0", "proposals": {}})
        proposal = proposals["proposals"].get(implementation["proposal_id"])
        if not proposal or proposal.get("status") != "ACCEPTED":
            raise ValueError("ACCEPTED_PROPOSAL_REQUIRED")
        if proposal["proposal_sha256"] != implementation["proposal_sha256"]:
            raise ValueError("IMPLEMENTATION_PROPOSAL_HASH_MISMATCH")

        targets = []
        for change in proposal["changes"]:
            path = _safe_target(change["path"])
            if _sha256_file(path) != change["preimage_sha256"]:
                raise ValueError("IMPLEMENTATION_PREIMAGE_STALE")
            targets.append((path, change))

        backup_root = BACKUPS_ROOT / implementation_id
        backup_root.mkdir(parents=True, exist_ok=True)
        applied = []
        try:
            for path, change in targets:
                backup_path = backup_root / change["path"]
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil_copy = path.read_bytes()
                backup_path.write_bytes(shutil_copy)
                _atomic_write_text(path, change["new_content"])
                if _sha256_file(path) != change["postimage_sha256"]:
                    raise RuntimeError("POSTIMAGE_HASH_MISMATCH")
                applied.append((path, backup_path, change))
        except Exception:
            for path, backup_path, _ in reversed(applied):
                if backup_path.is_file():
                    path.write_bytes(backup_path.read_bytes())
            raise

        implementation["status"] = "APPLIED_AWAITING_REVIEW"
        implementation["applied_at"] = _utc_now()
        implementation["backup_root_relative"] = _relative(backup_root)
        implementation["apply_token"] = None
        implementations["implementations"][implementation_id] = implementation
        _atomic_write_json(IMPLEMENTATIONS_FILE, implementations)

        proposal["applied"] = True
        proposals["proposals"][proposal["proposal_id"]] = proposal
        _atomic_write_json(PROPOSALS_FILE, proposals)

    _event("IMPLEMENTATION_APPLIED", implementation_id, {"change_count": len(targets), "manifest_sha256": implementation["implementation_manifest_sha256"]})
    return implementation


def _review_implementation(implementation_id: str, request: ImplementationReviewRequest) -> dict[str, Any]:
    with _LOCK:
        state = _read_json(IMPLEMENTATIONS_FILE, {"schema_version": "1.0.0", "implementations": {}})
        implementation = state["implementations"].get(implementation_id)
        if not implementation:
            raise ValueError("IMPLEMENTATION_NOT_FOUND")
        if implementation.get("status") != "APPLIED_AWAITING_REVIEW":
            raise ValueError("IMPLEMENTATION_NOT_READY_FOR_REVIEW")

        proposals = _read_json(PROPOSALS_FILE, {"schema_version": "1.0.0", "proposals": {}})
        proposal = proposals["proposals"][implementation["proposal_id"]]

        if request.decision == "ROLLBACK":
            backup_root = _resolve_relative(implementation["backup_root_relative"])
            for change in proposal["changes"]:
                path = _safe_target(change["path"])
                if _sha256_file(path) != change["postimage_sha256"]:
                    raise ValueError("ROLLBACK_POSTIMAGE_CHANGED")
            for change in proposal["changes"]:
                path = _safe_target(change["path"])
                backup = backup_root / change["path"]
                if not backup.is_file():
                    raise ValueError("ROLLBACK_BACKUP_MISSING")
                path.write_bytes(backup.read_bytes())
                if _sha256_file(path) != change["preimage_sha256"]:
                    raise RuntimeError("ROLLBACK_PREIMAGE_HASH_MISMATCH")
            implementation["status"] = "ROLLED_BACK"
            proposal["applied"] = False
            proposals["proposals"][proposal["proposal_id"]] = proposal
            _atomic_write_json(PROPOSALS_FILE, proposals)
        else:
            implementation["status"] = "ACCEPTED_IMPLEMENTATION"

        review = {
            "review_id": str(uuid.uuid4()),
            "entity_id": implementation_id,
            "entity_type": "implementations",
            "decision": request.decision,
            "reviewed_by": request.reviewed_by,
            "notes": request.notes,
            "reviewed_at": _utc_now(),
        }
        implementation["review"] = review
        state["implementations"][implementation_id] = implementation
        _atomic_write_json(IMPLEMENTATIONS_FILE, state)
        _append_jsonl(REVIEWS_FILE, review)

    _event("IMPLEMENTATION_REVIEWED", implementation_id, {"decision": request.decision, "reviewed_by": request.reviewed_by})
    return implementation


def _recompute_project_state() -> dict[str, Any]:
    plans = list(_read_json(PLANS_FILE, {"plans": {}}).get("plans", {}).values())
    proposals = list(_read_json(PROPOSALS_FILE, {"proposals": {}}).get("proposals", {}).values())
    implementations = list(_read_json(IMPLEMENTATIONS_FILE, {"implementations": {}}).get("implementations", {}).values())

    accepted_plans = sum(1 for item in plans if item.get("status") == "ACCEPTED")
    accepted_proposals = sum(1 for item in proposals if item.get("status") == "ACCEPTED")
    accepted_impl = sum(1 for item in implementations if item.get("status") == "ACCEPTED_IMPLEMENTATION")
    pending_impl = sum(1 for item in implementations if item.get("status") == "APPLIED_AWAITING_REVIEW")
    rejected = sum(1 for item in plans + proposals if item.get("status") == "REJECTED")

    score = min(100, accepted_plans * 15 + accepted_proposals * 20 + accepted_impl * 35)
    risks = []
    if pending_impl:
        risks.append("Applied implementation awaiting human review.")
    if not accepted_plans:
        risks.append("No accepted local-model plan yet.")
    if rejected:
        risks.append(f"{rejected} rejected planning or proposal artifacts require review.")

    current = _read_json(PROJECT_STATE_FILE, {"revision": 0})
    state = {
        "schema_version": "1.0.0",
        "revision": int(current.get("revision", 0)) + 1,
        "status": "CONTROLLED_OPERATIONAL" if accepted_impl or accepted_plans else "FOUNDATION_READY",
        "progress_percent": score,
        "counts": {
            "accepted_plans": accepted_plans,
            "accepted_proposals": accepted_proposals,
            "accepted_implementations": accepted_impl,
            "pending_implementation_reviews": pending_impl,
            "rejected_artifacts": rejected,
        },
        "risks": risks,
        "updated_at": _utc_now(),
        "derivation": "deterministic_runtime_state_only",
    }
    _atomic_write_json(PROJECT_STATE_FILE, state)
    _event("PROJECT_STATE_RECOMPUTED", str(state["revision"]), {"progress_percent": score, "risk_count": len(risks)})
    return state


def _run_readiness() -> dict[str, Any]:
    _ensure_state()
    models = _read_json(MODELS_FILE, {"models": {}}).get("models", {})
    implementations = _read_json(IMPLEMENTATIONS_FILE, {"implementations": {}}).get("implementations", {})
    baselines = _quality_baseline_summary()

    gates = [
        {
            "gate": "runtime_state_initialized",
            "status": "PASS",
            "details": RUNTIME_VERSION,
        },
        {
            "gate": "quality_baselines_present",
            "status": "PASS" if baselines else "HOLD",
            "details": len(baselines),
        },
        {
            "gate": "local_model_planning_approved",
            "status": "PASS" if any(item.get("state") == "PLANNING_APPROVED" for item in models.values()) else "HOLD",
            "details": [key for key, item in models.items() if item.get("state") == "PLANNING_APPROVED"],
        },
        {
            "gate": "no_applied_implementation_awaiting_review",
            "status": "PASS" if not any(item.get("status") == "APPLIED_AWAITING_REVIEW" for item in implementations.values()) else "HOLD",
            "details": sum(1 for item in implementations.values() if item.get("status") == "APPLIED_AWAITING_REVIEW"),
        },
        {
            "gate": "external_network_disabled",
            "status": "PASS",
            "details": "localhost Ollama only",
        },
        {
            "gate": "shell_git_self_apply_disabled",
            "status": "PASS",
            "details": True,
        },
    ]
    status = "READY_FOR_CONTROLLED_LOCAL_USE" if all(item["status"] == "PASS" for item in gates) else "HOLD"
    report = {
        "schema_version": "1.0.0",
        "readiness_id": str(uuid.uuid4()),
        "status": status,
        "gates": gates,
        "production_approval": "NOT_APPROVED",
        "staging_approval": "NOT_APPLICABLE_LOCAL_FIRST",
        "remote_integration": "NOT_CONNECTED_BY_DESIGN",
        "assessed_at": _utc_now(),
    }
    _atomic_write_json(READINESS_FILE, report)
    _event("PRODUCTION_READINESS_ASSESSED", report["readiness_id"], {"status": status, "production_approval": "NOT_APPROVED"})
    return report


def _cockpit() -> dict[str, Any]:
    _ensure_state()
    models = list(_read_json(MODELS_FILE, {"models": {}}).get("models", {}).values())
    plans = list(_read_json(PLANS_FILE, {"plans": {}}).get("plans", {}).values())
    proposals = list(_read_json(PROPOSALS_FILE, {"proposals": {}}).get("proposals", {}).values())
    implementations = list(_read_json(IMPLEMENTATIONS_FILE, {"implementations": {}}).get("implementations", {}).values())
    return {
        "result": "PASS",
        "summary": {
            "approved_models": sum(1 for item in models if item.get("state") == "PLANNING_APPROVED"),
            "plans_waiting_review": sum(1 for item in plans if item.get("status") == "HUMAN_REVIEW"),
            "accepted_plans": sum(1 for item in plans if item.get("status") == "ACCEPTED"),
            "proposals_waiting_review": sum(1 for item in proposals if item.get("status") == "HUMAN_REVIEW"),
            "approved_for_apply": sum(1 for item in implementations if item.get("status") == "APPROVED_FOR_APPLY"),
            "implementation_reviews": sum(1 for item in implementations if item.get("status") == "APPLIED_AWAITING_REVIEW"),
        },
        "models": models,
        "plans": sorted(plans, key=lambda item: item["created_at"], reverse=True)[:30],
        "proposals": sorted(proposals, key=lambda item: item["created_at"], reverse=True)[:30],
        "implementations": sorted(implementations, key=lambda item: item["approved_at"], reverse=True)[:30],
        "project_state": _read_json(PROJECT_STATE_FILE, {}),
        "readiness": _read_json(READINESS_FILE, {}),
    }


def _evidence(limit: int) -> list[dict[str, Any]]:
    if not EVIDENCE_FILE.is_file():
        return []
    lines = EVIDENCE_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-max(1, min(limit, 500)):] if line.strip()]


def _http_error(exc: Exception) -> HTTPException:
    message = str(exc)
    status = 404 if message.endswith("_NOT_FOUND") else 409
    if any(token in message for token in ["BLOCKED", "REQUIRED", "NOT_APPROVED", "REVALIDATION", "STALE", "MISMATCH"]):
        status = 403
    return HTTPException(status_code=status, detail=message)


@router.get("/api/v1/operational-core/full-stack-waves-3-8/health")
def health() -> dict[str, Any]:
    _ensure_state()
    return {
        "result": "PASS",
        "runtime_version": RUNTIME_VERSION,
        "waves": [3, 4, 5, 6, 7, 8],
        "local_model_inference": "planning_and_proposal_only",
        "local_model_transport": "127.0.0.1:11434_only",
        "external_network": "blocked",
        "shell": "blocked",
        "git": "blocked",
        "automatic_apply": "blocked",
        "human_approval": "required",
        "production_approval": "not_approved",
    }


@router.get("/api/v1/operational-core/full-stack-waves-3-8/cockpit")
def cockpit() -> dict[str, Any]:
    return _cockpit()


@router.get("/api/v1/operational-core/full-stack-waves-3-8/models")
def models() -> dict[str, Any]:
    _ensure_state()
    return _read_json(MODELS_FILE, {"schema_version": "1.0.0", "models": {}})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/models/probe")
def probe_models() -> dict[str, Any]:
    try:
        return {"result": "PASS", **_probe_models()}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/full-stack-waves-3-8/models/{model_id}/approve")
def approve_model(model_id: str, request: ModelApprovalRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "model": _approve_model(model_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/api/v1/operational-core/full-stack-waves-3-8/prompts")
def prompts() -> dict[str, Any]:
    return {
        "result": "PASS",
        "prompt_version": PROMPT_VERSION,
        "contracts": [
            {"prompt_id": "planning", "version": "1", "free_system_prompt": False, "output": "structured_json"},
            {"prompt_id": "change_proposal", "version": "1", "free_system_prompt": False, "output": "structured_json"},
        ],
    }


@router.get("/api/v1/operational-core/full-stack-waves-3-8/context-packs")
def context_packs() -> dict[str, Any]:
    _ensure_state()
    return _read_json(CONTEXTS_FILE, {"schema_version": "1.0.0", "context_packs": {}})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/context-packs")
def create_context(request: ContextRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "context_pack": _create_context(request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/api/v1/operational-core/full-stack-waves-3-8/plans")
def plans() -> dict[str, Any]:
    _ensure_state()
    return _read_json(PLANS_FILE, {"schema_version": "1.0.0", "plans": {}})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/plans/generate")
def generate_plan(request: PlanGenerateRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "plan": _generate_plan(request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/full-stack-waves-3-8/plans/{plan_id}/review")
def review_plan(plan_id: str, request: ReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "plan": _review_entity(PLANS_FILE, "plans", plan_id, request, "HUMAN_REVIEW")}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/api/v1/operational-core/full-stack-waves-3-8/proposals")
def proposals() -> dict[str, Any]:
    _ensure_state()
    return _read_json(PROPOSALS_FILE, {"schema_version": "1.0.0", "proposals": {}})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/proposals/generate")
def generate_proposal(request: ProposalGenerateRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "proposal": _generate_proposal(request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/full-stack-waves-3-8/proposals/{proposal_id}/review")
def review_proposal(proposal_id: str, request: ReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "proposal": _review_entity(PROPOSALS_FILE, "proposals", proposal_id, request, "HUMAN_REVIEW")}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/api/v1/operational-core/full-stack-waves-3-8/implementations")
def implementations() -> dict[str, Any]:
    _ensure_state()
    return _read_json(IMPLEMENTATIONS_FILE, {"schema_version": "1.0.0", "implementations": {}})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/implementations/prepare")
def prepare_implementation(request: ImplementationPrepareRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "implementation": _prepare_implementation(request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/full-stack-waves-3-8/implementations/{implementation_id}/apply")
def apply_implementation(implementation_id: str, request: ApplyRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "implementation": _apply_implementation(implementation_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/full-stack-waves-3-8/implementations/{implementation_id}/review")
def review_implementation(implementation_id: str, request: ImplementationReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "implementation": _review_implementation(implementation_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.get("/api/v1/operational-core/full-stack-waves-3-8/project-state")
def project_state() -> dict[str, Any]:
    _ensure_state()
    return _read_json(PROJECT_STATE_FILE, {})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/project-state/recompute")
def recompute_project_state() -> dict[str, Any]:
    return {"result": "PASS", "project_state": _recompute_project_state()}


@router.get("/api/v1/operational-core/full-stack-waves-3-8/readiness")
def readiness() -> dict[str, Any]:
    _ensure_state()
    return _read_json(READINESS_FILE, {})


@router.post("/api/v1/operational-core/full-stack-waves-3-8/readiness/run")
def run_readiness() -> dict[str, Any]:
    return {"result": "PASS", "readiness": _run_readiness()}


@router.get("/api/v1/operational-core/full-stack-waves-3-8/evidence")
def evidence(limit: int = 200) -> dict[str, Any]:
    return {"result": "PASS", "events": _evidence(limit)}


@router.get("/api/v1/operational-core/full-stack-waves-3-8/governance")
def governance() -> dict[str, Any]:
    return {
        "result": "PASS",
        "waves": {
            "3": "controlled_local_model_planning",
            "4": "sandboxed_change_proposal",
            "5": "human_approved_implementation",
            "6": "unified_operations_cockpit",
            "7": "deterministic_project_state_intelligence",
            "8": "controlled_local_readiness_closure",
        },
        "boundaries": health(),
        "source_write": "wave_5_only_after_explicit_human_approval_and_one_time_token",
        "rollback": "hash_guarded",
        "production_approval": "NOT_APPROVED",
    }
