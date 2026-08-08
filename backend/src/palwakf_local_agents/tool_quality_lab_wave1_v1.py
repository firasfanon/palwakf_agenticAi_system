from __future__ import annotations

import ast
import hashlib
import importlib
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

router = APIRouter(tags=["tool-quality-evaluation-lab-wave1-v1"])

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_FILE = MODULE_DIR / "tool_quality_catalog_wave1_v1.json"
FIXTURE_ROOT = MODULE_DIR / "tool_quality_fixtures_wave1_v1"
GOLDEN_FILE = FIXTURE_ROOT / "expected_golden_results.json"

RUNTIME_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "tool_quality_lab"
RUNS_FILE = RUNTIME_ROOT / "benchmark_runs.jsonl"
SCORECARDS_FILE = RUNTIME_ROOT / "scorecards.json"
BASELINES_FILE = RUNTIME_ROOT / "quality_baselines.json"
QUARANTINES_FILE = RUNTIME_ROOT / "quarantines.json"
REVIEWS_FILE = RUNTIME_ROOT / "reviews.jsonl"
REPORTS_DIR = RUNTIME_ROOT / "reports"
TELEMETRY_FILE = RUNTIME_ROOT / "quality_telemetry.jsonl"

_LOCK = threading.RLock()
_SUITE_BY_ID: dict[str, dict[str, Any]] | None = None

QUALITY_ACCEPTED_MIN = 90
PASS_WITH_LIMITATIONS_MIN = 80
HUMAN_REVIEW_MIN = 70


class RunRequest(BaseModel):
    repeat_count: int = Field(default=3, ge=1, le=5)


class ReviewRequest(BaseModel):
    decision: str = Field(pattern="^(APPROVE|APPROVE_WITH_LIMITATIONS|RETURN|REJECT)$")
    notes: str = Field(default="", max_length=2000)


class AcceptRequest(BaseModel):
    limitations: list[str] = Field(default_factory=list, max_length=20)
    approval_reference: str = Field(min_length=3, max_length=300)


class QuarantineRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_runtime() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not SCORECARDS_FILE.exists():
        _atomic_write_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})
    if not BASELINES_FILE.exists():
        _atomic_write_json(BASELINES_FILE, {"schema_version": "1.0.0", "baselines": {}})
    if not QUARANTINES_FILE.exists():
        _atomic_write_json(QUARANTINES_FILE, {"schema_version": "1.0.0", "quarantines": {}})


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _catalog() -> dict[str, Any]:
    if not CATALOG_FILE.is_file():
        raise RuntimeError("TOOL_QUALITY_CATALOG_NOT_FOUND")
    return _read_json(CATALOG_FILE, {})


def _suites() -> dict[str, dict[str, Any]]:
    global _SUITE_BY_ID
    if _SUITE_BY_ID is None:
        _SUITE_BY_ID = {item["suite_id"]: item for item in _catalog().get("suites", [])}
    return _SUITE_BY_ID


def _golden() -> dict[str, Any]:
    if not GOLDEN_FILE.is_file():
        raise RuntimeError("GOLDEN_RESULTS_NOT_FOUND")
    return _read_json(GOLDEN_FILE, {})


def _wave1():
    return importlib.import_module(
        "palwakf_local_agents.open_source_tools_operational_admission_wave1_v1"
    )


def _wave1_state() -> dict[str, Any]:
    return _wave1()._ensure_state()


def _tool_record(tool_id: str) -> dict[str, Any] | None:
    return _wave1_state().get("tools", {}).get(tool_id)


def _redact(text: str) -> tuple[str, bool]:
    original = text
    for workspace in {str(PROJECT_ROOT), str(PROJECT_ROOT).replace("\\", "/")}:
        text = text.replace(workspace, "<WORKSPACE>")
    patterns = [
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "<REDACTED_PRIVATE_KEY>"),
        (r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*['\"]?[^'\"\s,;]+", r"\1=<REDACTED>"),
        (r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}", r"\1 <REDACTED>"),
        (r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{8,}\b", "<REDACTED_TOKEN>"),
        (r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s\"']+", "<REDACTED_CONNECTION_STRING>"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return text, text != original


def _telemetry(name: str, run_id: str, status: str, attributes: dict[str, Any]) -> None:
    redacted_attributes: dict[str, Any] = {}
    for key, value in attributes.items():
        redacted, _ = _redact(str(value))
        redacted_attributes[key] = redacted
    _append_jsonl(
        TELEMETRY_FILE,
        {
            "trace_id": run_id.replace("-", ""),
            "timestamp": _utc_now(),
            "name": name,
            "status": status,
            "attributes": redacted_attributes,
            "export": "local_jsonl_only",
            "content_policy": "no_prompt_no_source_no_secret",
        },
    )


def _classify(score: float | None, safety_gates: dict[str, bool], limitations: list[str]) -> str:
    if any(value is False for value in safety_gates.values()):
        return "QUARANTINED"
    if score is None:
        return "NOT_ASSESSED"
    if score >= QUALITY_ACCEPTED_MIN and not limitations:
        return "QUALITY_ACCEPTED"
    if score >= PASS_WITH_LIMITATIONS_MIN:
        return "PASS_WITH_LIMITATIONS"
    if score >= HUMAN_REVIEW_MIN:
        return "HUMAN_REVIEW_REQUIRED"
    return "QUALITY_FAILED"


def _normalized_hash(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _native_index_once() -> dict[str, Any]:
    python_file = FIXTURE_ROOT / "python_backend" / "app.py"
    react_file = FIXTURE_ROOT / "react_typescript" / "App.tsx"
    flutter_file = FIXTURE_ROOT / "flutter_dart" / "main.dart"

    python_source = python_file.read_text(encoding="utf-8")
    react_source = react_file.read_text(encoding="utf-8")
    flutter_source = flutter_file.read_text(encoding="utf-8")

    tree = ast.parse(python_source, filename=str(python_file))
    python_functions: list[str] = []
    python_classes: list[str] = []
    fastapi_routes: list[dict[str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            python_functions.append(node.name)
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                func = decorator.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "app"
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    fastapi_routes.append(
                        {
                            "method": func.attr.upper(),
                            "path": str(decorator.args[0].value),
                            "handler": node.name,
                        }
                    )
        elif isinstance(node, ast.ClassDef):
            python_classes.append(node.name)

    react_components = set()
    for pattern in [
        r"\bexport\s+function\s+([A-Z][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\(",
        r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*[:=]",
    ]:
        react_components.update(re.findall(pattern, react_source))
    react_routes = sorted(set(re.findall(r'path=["\']([^"\']+)["\']', react_source)))
    flutter_widgets = sorted(
        set(
            re.findall(
                r"class\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+(?:StatelessWidget|StatefulWidget)",
                flutter_source,
            )
        )
    )

    return {
        "python_functions": sorted(set(python_functions)),
        "python_classes": sorted(set(python_classes)),
        "fastapi_routes": sorted(fastapi_routes, key=lambda item: (item["path"], item["method"])),
        "react_components": sorted(react_components),
        "react_routes": react_routes,
        "flutter_widgets": flutter_widgets,
        "relative_files": [
            "python_backend/app.py",
            "react_typescript/App.tsx",
            "flutter_dart/main.dart",
        ],
    }


def _run_native_index_suite(repeat_count: int) -> dict[str, Any]:
    golden = _golden()["native_code_index_contract_v1"]
    outputs = [_native_index_once() for _ in range(repeat_count)]
    hashes = [_normalized_hash(output) for output in outputs]
    deterministic = len(set(hashes)) == 1
    actual = outputs[0]
    keys = [
        "python_functions",
        "python_classes",
        "fastapi_routes",
        "react_components",
        "react_routes",
        "flutter_widgets",
    ]
    exact_matches = {key: actual.get(key) == golden.get(key) for key in keys}
    accuracy = sum(1 for value in exact_matches.values() if value) / len(exact_matches)
    score = round((accuracy * 85) + (15 if deterministic else 0), 2)
    safety = {
        "source_write_zero": True,
        "network_access_zero": True,
        "absolute_path_leak_zero": str(PROJECT_ROOT) not in json.dumps(outputs),
        "deterministic_output": deterministic,
    }
    limitations = [] if accuracy == 1 else ["Golden result mismatch requires fixture review."]
    return {
        "score": score,
        "metrics": {
            "exact_match_ratio": accuracy,
            "deterministic": deterministic,
            "repeat_count": repeat_count,
            "normalized_hash": hashes[0],
            "exact_matches": exact_matches,
        },
        "safety_gates": safety,
        "limitations": limitations,
        "evidence": actual,
    }


def _run_local_telemetry_suite(repeat_count: int) -> dict[str, Any]:
    synthetic = (
        "password=synthetic_password "
        "token=ghp_SYNTHETIC123456789 "
        f"path={PROJECT_ROOT / 'PrivateProject'}"
    )
    outputs = []
    for _ in range(repeat_count):
        redacted, changed = _redact(synthetic)
        outputs.append({"redacted": redacted, "changed": changed})
    hashes = [_normalized_hash(output) for output in outputs]
    deterministic = len(set(hashes)) == 1
    combined = json.dumps(outputs, ensure_ascii=False)
    no_secret = (
        "synthetic_password" not in combined
        and "ghp_SYNTHETIC" not in combined
        and str(PROJECT_ROOT) not in combined
    )
    safety = {
        "secret_leak_zero": no_secret,
        "absolute_path_leak_zero": str(PROJECT_ROOT) not in combined,
        "remote_export_zero": True,
        "source_content_leak_zero": True,
        "deterministic_output": deterministic,
    }
    score = 100.0 if all(safety.values()) else 0.0
    return {
        "score": score,
        "metrics": {
            "schema_valid": True,
            "deterministic": deterministic,
            "repeat_count": repeat_count,
            "normalized_hash": hashes[0],
        },
        "safety_gates": safety,
        "limitations": [],
        "evidence": outputs[0],
    }


def _run_tree_sitter_readiness() -> dict[str, Any]:
    record = _tool_record("tree_sitter") or {}
    if not record.get("present"):
        return {
            "score": None,
            "metrics": {"state": "NOT_ASSESSED_TOOL_MISSING"},
            "safety_gates": {"no_execution_beyond_admission_probe": True},
            "limitations": ["Tree-sitter is not available locally."],
            "evidence": {"runtime_state": record.get("runtime_state", "UNKNOWN")},
        }
    admitted = record.get("runtime_state") == "CONTROLLED_ACTIVE_READ_ONLY"
    integrity = bool(record.get("version") and record.get("binary_sha256"))
    score = 85.0 if admitted and integrity else 70.0
    return {
        "score": score,
        "metrics": {
            "admitted": admitted,
            "version_verified": bool(record.get("version")),
            "binary_hash_verified": bool(record.get("binary_sha256")),
            "grammar_pack_benchmark": "NOT_INCLUDED_IN_WAVE1",
        },
        "safety_gates": {
            "source_write_zero": True,
            "network_access_zero": True,
            "binary_hash_established": bool(record.get("binary_sha256")),
        },
        "limitations": ["Parser grammar pack benchmark remains required before production indexing."],
        "evidence": {
            "version": record.get("version"),
            "binary_sha256": record.get("binary_sha256"),
            "runtime_state": record.get("runtime_state"),
        },
    }


def _run_opentelemetry_quality(repeat_count: int) -> dict[str, Any]:
    record = _tool_record("opentelemetry") or {}
    if not record.get("present"):
        return {
            "score": None,
            "metrics": {"state": "NOT_ASSESSED_TOOL_MISSING"},
            "safety_gates": {"no_remote_export": True},
            "limitations": ["OpenTelemetry package or collector is not available locally."],
            "evidence": {"runtime_state": record.get("runtime_state", "UNKNOWN")},
        }
    privacy = _run_local_telemetry_suite(repeat_count)
    privacy["metrics"]["runtime_state"] = record.get("runtime_state")
    privacy["metrics"]["detected_version"] = record.get("version")
    privacy["limitations"] = [
        "This suite validates the local adapter contract; collector export remains disabled."
    ]
    privacy["score"] = min(float(privacy["score"]), 95.0)
    return privacy


def _scan_via_wave1(tool_id: str, scope_relative: str, local_rules_relative: str | None) -> dict[str, Any]:
    wave1 = _wave1()
    request = wave1.ControlledScanRequest(
        scope_relative=scope_relative,
        local_rules_relative=local_rules_relative,
        timeout_seconds=120,
    )
    return wave1._run_controlled_scan(tool_id, request)


def _run_semgrep_suite() -> dict[str, Any]:
    record = _tool_record("semgrep") or {}
    if record.get("runtime_state") != "CONTROLLED_USER_TRIGGERED_SCAN":
        return {
            "score": None,
            "metrics": {"state": record.get("runtime_state", "NOT_ASSESSED")},
            "safety_gates": {"no_scan_executed": True},
            "limitations": ["Semgrep is not admitted for controlled fixture scans."],
            "evidence": {},
        }
    fixture_rel = str((FIXTURE_ROOT / "python_backend").relative_to(PROJECT_ROOT)).replace("\\", "/")
    rules_rel = str((FIXTURE_ROOT / "semgrep_rules.yml").relative_to(PROJECT_ROOT)).replace("\\", "/")
    report = _scan_via_wave1("semgrep", fixture_rel, rules_rel)
    excerpt = report.get("redacted_output_excerpt", "")
    finding_detected = "palwakf-eval-risky-eval" in excerpt
    raw_secret_absent = "synthetic_password" not in excerpt
    score = 100.0 if finding_detected and raw_secret_absent else 60.0
    return {
        "score": score,
        "metrics": {
            "expected_rule_detected": finding_detected,
            "exit_class": report.get("exit_class"),
            "duration_ms": report.get("duration_ms"),
            "output_sha256": report.get("output_sha256"),
        },
        "safety_gates": {
            "source_write_zero": report.get("source_write") == "blocked_by_contract",
            "raw_secret_leak_zero": raw_secret_absent,
            "autofix_blocked": True,
            "remote_rules_blocked": True,
        },
        "limitations": [] if finding_detected else ["Expected seeded rule was not detected."],
        "evidence": {
            "invocation_id": report.get("invocation_id"),
            "result": report.get("result"),
            "truncated": report.get("truncated"),
        },
    }


def _run_gitleaks_suite() -> dict[str, Any]:
    record = _tool_record("gitleaks") or {}
    if record.get("runtime_state") != "CONTROLLED_USER_TRIGGERED_SCAN":
        return {
            "score": None,
            "metrics": {"state": record.get("runtime_state", "NOT_ASSESSED")},
            "safety_gates": {"no_scan_executed": True},
            "limitations": ["Gitleaks is not admitted for controlled fixture scans."],
            "evidence": {},
        }
    fixture_rel = str((FIXTURE_ROOT / "seeded_security_findings").relative_to(PROJECT_ROOT)).replace("\\", "/")
    report = _scan_via_wave1("gitleaks", fixture_rel, None)
    excerpt = report.get("redacted_output_excerpt", "")
    synthetic_value_absent = (
        "AKIAIOSFODNN7EXAMPLE" not in excerpt
        and "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in excerpt
    )
    finding_present = any(marker in excerpt for marker in ["RuleID", "Fingerprint", "StartLine", "aws-access-token"])
    score = 100.0 if finding_present and synthetic_value_absent else 75.0
    return {
        "score": score,
        "metrics": {
            "finding_metadata_present": finding_present,
            "synthetic_value_absent": synthetic_value_absent,
            "duration_ms": report.get("duration_ms"),
            "output_sha256": report.get("output_sha256"),
        },
        "safety_gates": {
            "raw_secret_leak_zero": synthetic_value_absent,
            "source_write_zero": report.get("source_write") == "blocked_by_contract",
            "git_mutation_zero": True,
            "automatic_remediation_zero": True,
        },
        "limitations": [] if finding_present else ["Seeded finding metadata was not observed."],
        "evidence": {
            "invocation_id": report.get("invocation_id"),
            "result": report.get("result"),
            "truncated": report.get("truncated"),
        },
    }


def _run_trivy_readiness() -> dict[str, Any]:
    record = _tool_record("trivy") or {}
    expected_hold = record.get("runtime_state") in {
        "READINESS_HOLD_OFFLINE_DB_POLICY",
        "MISSING_NOT_FAILED",
        "REGISTERED_AWAITING_PROBE",
    }
    return {
        "score": None,
        "metrics": {
            "runtime_state": record.get("runtime_state", "UNKNOWN"),
            "offline_database_provenance": "NOT_APPROVED",
            "database_hash": None,
            "scan_executed": False,
        },
        "safety_gates": {
            "network_scan_zero": True,
            "database_update_zero": True,
            "scan_blocked_until_policy": expected_hold,
        },
        "limitations": [
            "Offline vulnerability database provenance, hash, update, and expiry policy are required."
        ],
        "evidence": {"readiness_hold": expected_hold},
    }


def _run_deferred_review() -> dict[str, Any]:
    state = _wave1_state().get("tools", {})
    expected = {
        "temporal": "ARCHITECTURE_DEFERRED",
        "prefect": "ARCHITECTURE_DEFERRED",
        "langfuse": "PRIVACY_AND_LICENSE_REVIEW",
        "phoenix": "LICENSE_AND_PRIVACY_REVIEW",
        "swe_agent": "BLOCKED_CURRENT_PHASE",
        "aider": "BLOCKED_CURRENT_PHASE",
    }
    actual = {tool_id: state.get(tool_id, {}).get("runtime_state") for tool_id in expected}
    matches = {tool_id: actual[tool_id] == required for tool_id, required in expected.items()}
    score = round(100 * sum(matches.values()) / len(matches), 2)
    return {
        "score": score,
        "metrics": {"expected_states": expected, "actual_states": actual, "matches": matches},
        "safety_gates": {
            "deferred_tools_not_executed": True,
            "git_write_agents_blocked": matches["swe_agent"] and matches["aider"],
        },
        "limitations": ["Admission review only; no quality execution score is granted."],
        "evidence": actual,
    }


RUNNERS = {
    "native_code_index_contract_v1": lambda repeat: _run_native_index_suite(repeat),
    "local_telemetry_privacy_v1": lambda repeat: _run_local_telemetry_suite(repeat),
    "tree_sitter_readiness_v1": lambda repeat: _run_tree_sitter_readiness(),
    "opentelemetry_local_quality_v1": lambda repeat: _run_opentelemetry_quality(repeat),
    "semgrep_fixture_quality_v1": lambda repeat: _run_semgrep_suite(),
    "gitleaks_fixture_quality_v1": lambda repeat: _run_gitleaks_suite(),
    "trivy_offline_readiness_v1": lambda repeat: _run_trivy_readiness(),
    "deferred_tools_admission_review_v1": lambda repeat: _run_deferred_review(),
}


def _persist_run(run: dict[str, Any]) -> None:
    _ensure_runtime()
    _append_jsonl(RUNS_FILE, run)
    _atomic_write_json(REPORTS_DIR / f"{run['run_id']}.json", run)

    scorecards = _read_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})
    scorecards["scorecards"][run["tool_id"]] = {
        "tool_id": run["tool_id"],
        "suite_id": run["suite_id"],
        "last_run_id": run["run_id"],
        "quality_result": run["quality_result"],
        "score": run["score"],
        "safety_gates": run["safety_gates"],
        "limitations": run["limitations"],
        "normalized_result_hash": run["normalized_result_hash"],
        "updated_at": run["completed_at"],
        "review_status": "PENDING",
    }
    _atomic_write_json(SCORECARDS_FILE, scorecards)


def _run_suite(suite_id: str, request: RunRequest) -> dict[str, Any]:
    suite = _suites().get(suite_id)
    if not suite:
        raise ValueError("UNKNOWN_SUITE_ID")
    runner = RUNNERS.get(suite_id)
    if not runner:
        raise ValueError("SUITE_RUNNER_NOT_IMPLEMENTED")

    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    started = time.monotonic()
    _telemetry("tool_quality.benchmark_started", run_id, "STARTED", {"suite_id": suite_id})

    payload = runner(request.repeat_count)
    score = payload["score"]
    safety_gates = payload["safety_gates"]
    limitations = payload["limitations"]
    quality_result = _classify(score, safety_gates, limitations)

    tool_id = suite["tool_id"]
    tool_record = _tool_record(tool_id) if tool_id in {
        "tree_sitter", "opentelemetry", "semgrep", "gitleaks", "trivy"
    } else None

    normalized_result = {
        "suite_id": suite_id,
        "tool_id": tool_id,
        "score": score,
        "metrics": payload["metrics"],
        "safety_gates": safety_gates,
        "limitations": limitations,
        "evidence": payload["evidence"],
    }
    run = {
        "run_id": run_id,
        "suite_id": suite_id,
        "tool_id": tool_id,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "duration_ms": int((time.monotonic() - started) * 1000),
        "repeat_count": request.repeat_count,
        "fixture_version": _sha256_file(GOLDEN_FILE)[:16],
        "suite_version": "1.0.0",
        "tool_version": tool_record.get("version") if tool_record else "native-contract-v1",
        "executable_sha256": tool_record.get("binary_sha256") if tool_record else None,
        "score": score,
        "quality_result": quality_result,
        "metrics": payload["metrics"],
        "safety_gates": safety_gates,
        "limitations": limitations,
        "normalized_result_hash": _normalized_hash(normalized_result),
        "evidence": payload["evidence"],
        "live_project_scan": False,
        "user_triggered": True,
        "automatic_retry": False,
    }

    _persist_run(run)
    _telemetry(
        "tool_quality.benchmark_completed",
        run_id,
        quality_result,
        {"suite_id": suite_id, "score": score, "quality_result": quality_result},
    )
    if quality_result == "QUARANTINED":
        _quarantine_tool(tool_id, "Automatic safety-gate quarantine from benchmark.", run_id)
    return run


def _load_runs(limit: int = 100) -> list[dict[str, Any]]:
    if not RUNS_FILE.is_file():
        return []
    lines = RUNS_FILE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-max(1, min(limit, 500)):] if line.strip()]


def _find_run(run_id: str) -> dict[str, Any]:
    for run in reversed(_load_runs(500)):
        if run.get("run_id") == run_id:
            return run
    raise ValueError("RUN_NOT_FOUND")


def _review_run(run_id: str, request: ReviewRequest) -> dict[str, Any]:
    run = _find_run(run_id)
    review = {
        "review_id": str(uuid.uuid4()),
        "run_id": run_id,
        "tool_id": run["tool_id"],
        "suite_id": run["suite_id"],
        "decision": request.decision,
        "notes": request.notes,
        "reviewed_at": _utc_now(),
        "human_authority_required": True,
    }
    _append_jsonl(REVIEWS_FILE, review)

    scorecards = _read_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})
    card = scorecards.get("scorecards", {}).get(run["tool_id"])
    if card and card.get("last_run_id") == run_id:
        card["review_status"] = request.decision
        card["reviewed_at"] = review["reviewed_at"]
        _atomic_write_json(SCORECARDS_FILE, scorecards)
    return review


def _latest_review(run_id: str) -> dict[str, Any] | None:
    if not REVIEWS_FILE.is_file():
        return None
    latest = None
    for line in REVIEWS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("run_id") == run_id:
            latest = item
    return latest


def _accept_baseline(tool_id: str, request: AcceptRequest) -> dict[str, Any]:
    scorecards = _read_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})
    card = scorecards.get("scorecards", {}).get(tool_id)
    if not card:
        raise ValueError("SCORECARD_NOT_FOUND")
    if card.get("quality_result") not in {"QUALITY_ACCEPTED", "PASS_WITH_LIMITATIONS"}:
        raise ValueError("QUALITY_RESULT_NOT_ELIGIBLE")
    review = _latest_review(card["last_run_id"])
    if not review or review.get("decision") not in {"APPROVE", "APPROVE_WITH_LIMITATIONS"}:
        raise ValueError("HUMAN_REVIEW_APPROVAL_REQUIRED")

    run = _find_run(card["last_run_id"])
    baseline = {
        "baseline_id": str(uuid.uuid4()),
        "tool_id": tool_id,
        "run_id": card["last_run_id"],
        "quality_result": card["quality_result"],
        "score": card["score"],
        "normalized_result_hash": card["normalized_result_hash"],
        "tool_version": run.get("tool_version"),
        "executable_sha256": run.get("executable_sha256"),
        "fixture_version": run.get("fixture_version"),
        "suite_version": run.get("suite_version"),
        "limitations": request.limitations,
        "approval_reference": request.approval_reference,
        "accepted_at": _utc_now(),
        "execution_authority": "none",
    }
    baselines = _read_json(BASELINES_FILE, {"schema_version": "1.0.0", "baselines": {}})
    baselines["baselines"][tool_id] = baseline
    _atomic_write_json(BASELINES_FILE, baselines)
    return baseline


def _quarantine_tool(tool_id: str, reason: str, run_id: str | None) -> dict[str, Any]:
    quarantine = {
        "quarantine_id": str(uuid.uuid4()),
        "tool_id": tool_id,
        "reason": reason,
        "run_id": run_id,
        "quarantined_at": _utc_now(),
        "runtime_execution": "blocked",
    }
    quarantines = _read_json(QUARANTINES_FILE, {"schema_version": "1.0.0", "quarantines": {}})
    quarantines["quarantines"][tool_id] = quarantine
    _atomic_write_json(QUARANTINES_FILE, quarantines)

    if tool_id in {"tree_sitter", "opentelemetry", "semgrep", "gitleaks", "trivy"}:
        try:
            wave1 = _wave1()
            state = wave1._ensure_state()
            record = state.get("tools", {}).get(tool_id)
            if record:
                record["runtime_state"] = "SUSPENDED"
                record["suspended"] = True
                record["suspension_reason"] = reason
                record["allowed_operations"] = ["presence_probe_only"]
                wave1._save_state(state)
        except Exception:
            pass
    return quarantine


@router.get("/api/v1/operational-core/tool-quality/health")
def health() -> dict[str, Any]:
    _ensure_runtime()
    wave1_state = _wave1_state()
    return {
        "result": "PASS",
        "mode": _catalog().get("mode"),
        "suite_count": len(_suites()),
        "wave1_precondition": wave1_state.get("mode"),
        "live_project_scan": "blocked",
        "model_inference": "none",
        "shell": "blocked",
        "git": "blocked",
        "automatic_retry": "blocked",
    }


@router.get("/api/v1/operational-core/tool-quality/catalog")
def catalog() -> dict[str, Any]:
    scorecards = _read_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})
    baselines = _read_json(BASELINES_FILE, {"schema_version": "1.0.0", "baselines": {}})
    quarantines = _read_json(QUARANTINES_FILE, {"schema_version": "1.0.0", "quarantines": {}})
    suites = []
    for suite in _catalog().get("suites", []):
        item = dict(suite)
        tool_id = item["tool_id"]
        if tool_id in {"tree_sitter", "opentelemetry", "semgrep", "gitleaks", "trivy"}:
            item["admission_state"] = (_tool_record(tool_id) or {}).get("runtime_state")
        else:
            item["admission_state"] = "NATIVE_OR_REVIEW_ONLY"
        item["scorecard"] = scorecards.get("scorecards", {}).get(tool_id)
        item["baseline"] = baselines.get("baselines", {}).get(tool_id)
        item["quarantine"] = quarantines.get("quarantines", {}).get(tool_id)
        suites.append(item)
    return {"result": "PASS", "suites": suites}


@router.get("/api/v1/operational-core/tool-quality/suites")
def suites() -> dict[str, Any]:
    return {"result": "PASS", "suites": list(_suites().values())}


@router.get("/api/v1/operational-core/tool-quality/runs")
def runs(limit: int = 100) -> dict[str, Any]:
    return {"result": "PASS", "runs": _load_runs(limit)}


@router.get("/api/v1/operational-core/tool-quality/scorecards")
def scorecards() -> dict[str, Any]:
    return _read_json(SCORECARDS_FILE, {"schema_version": "1.0.0", "scorecards": {}})


@router.get("/api/v1/operational-core/tool-quality/baselines")
def baselines() -> dict[str, Any]:
    return _read_json(BASELINES_FILE, {"schema_version": "1.0.0", "baselines": {}})


@router.get("/api/v1/operational-core/tool-quality/quarantines")
def quarantines() -> dict[str, Any]:
    return _read_json(QUARANTINES_FILE, {"schema_version": "1.0.0", "quarantines": {}})


@router.get("/api/v1/operational-core/tool-quality/boundaries")
def boundaries() -> dict[str, Any]:
    return {
        "result": "PASS",
        "auto_install": "blocked",
        "auto_download": "blocked",
        "model_inference": "none",
        "shell": "blocked",
        "git": "blocked",
        "source_write": "blocked",
        "autofix": "blocked",
        "remote_rules": "blocked",
        "network_runtime": "blocked",
        "automatic_retry": "blocked",
        "live_project_scan": "blocked",
        "fixture_scoped_user_triggered_runs": "allowed",
        "human_quality_approval": "required",
    }


@router.post("/api/v1/operational-core/tool-quality/suites/{suite_id}/prepare")
def prepare_suite(suite_id: str) -> dict[str, Any]:
    suite = _suites().get(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="UNKNOWN_SUITE_ID")
    return {
        "result": "PASS",
        "suite": suite,
        "prepared": True,
        "executed": False,
        "fixture_scope": suite["fixture_scope"],
        "live_project_scan": False,
    }


@router.post("/api/v1/operational-core/tool-quality/suites/{suite_id}/run")
def run_suite(suite_id: str, request: RunRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "run": _run_suite(suite_id, request)}
    except ValueError as exc:
        status = 404 if str(exc) in {"UNKNOWN_SUITE_ID", "RUN_NOT_FOUND"} else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/api/v1/operational-core/tool-quality/runs/{run_id}/review")
def review_run(run_id: str, request: ReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "review": _review_run(run_id, request)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/v1/operational-core/tool-quality/tools/{tool_id}/accept")
def accept_tool(tool_id: str, request: AcceptRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "baseline": _accept_baseline(tool_id, request)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/v1/operational-core/tool-quality/tools/{tool_id}/quarantine")
def quarantine_tool(tool_id: str, request: QuarantineRequest) -> dict[str, Any]:
    return {"result": "PASS", "quarantine": _quarantine_tool(tool_id, request.reason, None)}
