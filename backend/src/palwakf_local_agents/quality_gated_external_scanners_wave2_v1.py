from __future__ import annotations

import hashlib
import importlib
import json
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["quality-gated-external-scanners-wave2-v1"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "external_scanners_wave2"
TASKS_FILE = RUNTIME_ROOT / "scan_tasks.json"
MANIFESTS_FILE = RUNTIME_ROOT / "scan_manifests.json"
RUNS_FILE = RUNTIME_ROOT / "scan_runs.json"
REVIEWS_FILE = RUNTIME_ROOT / "scan_reviews.jsonl"
EVIDENCE_FILE = RUNTIME_ROOT / "scan_evidence.jsonl"
CHECKPOINTS_FILE = RUNTIME_ROOT / "scan_checkpoints.json"

QUALITY_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "tool_quality_lab"
BASELINES_FILE = QUALITY_ROOT / "quality_baselines.json"
QUARANTINES_FILE = QUALITY_ROOT / "quarantines.json"

ADMISSION_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "open_source_tools_wave1"
ADMISSION_STATE_FILE = ADMISSION_ROOT / "tool_admission_wave1_state.json"

_LOCK = threading.RLock()
MAX_RESULT_EXCERPT = 64_000
SCANNER_CONTRACT_VERSION = "1.0.0"

SCANNERS: dict[str, dict[str, Any]] = {
    "semgrep": {
        "label_ar": "Semgrep",
        "description_ar": "تحليل ساكن بقواعد محلية معتمدة فقط.",
        "required_admission_state": "CONTROLLED_USER_TRIGGERED_SCAN",
        "required_quality_key": "semgrep",
        "rules_required": True,
        "operation": "controlled_project_scoped_static_scan",
    },
    "gitleaks": {
        "label_ar": "Gitleaks",
        "description_ar": "كشف أسرار مع حجب كامل لقيم الأسرار.",
        "required_admission_state": "CONTROLLED_USER_TRIGGERED_SCAN",
        "required_quality_key": "gitleaks",
        "rules_required": False,
        "operation": "controlled_project_scoped_secret_scan",
    },
    "trivy": {
        "label_ar": "Trivy",
        "description_ar": "محجوب حتى اعتماد قاعدة ثغرات Offline وسياسة منشئها وتحديثها.",
        "required_admission_state": "READINESS_HOLD_OFFLINE_DB_POLICY",
        "required_quality_key": "trivy",
        "rules_required": False,
        "operation": "readiness_hold_only",
    },
}


class CreateScanTaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    purpose: str = Field(min_length=3, max_length=3000)
    scanner_id: str
    scope_relative: str = Field(default=".", max_length=500)
    local_rules_relative: str | None = Field(default=None, max_length=500)
    timeout_seconds: int = Field(default=120, ge=10, le=180)
    operator_notes: str = Field(default="", max_length=2000)


class ApprovalRequest(BaseModel):
    approval_reference: str = Field(min_length=3, max_length=300)
    approved_by: str = Field(min_length=2, max_length=120)


class ResultReviewRequest(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|RETURN|REJECT)$")
    notes: str = Field(default="", max_length=2000)
    reviewed_by: str = Field(min_length=2, max_length=120)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _ensure_state() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        _atomic_write_json(TASKS_FILE, {"schema_version": "1.0.0", "tasks": {}})
    if not MANIFESTS_FILE.exists():
        _atomic_write_json(MANIFESTS_FILE, {"schema_version": "1.0.0", "manifests": {}})
    if not RUNS_FILE.exists():
        _atomic_write_json(RUNS_FILE, {"schema_version": "1.0.0", "runs": {}})
    if not CHECKPOINTS_FILE.exists():
        _atomic_write_json(CHECKPOINTS_FILE, {"schema_version": "1.0.0", "checkpoints": {}})


def _load_tasks() -> dict[str, Any]:
    _ensure_state()
    return _read_json(TASKS_FILE, {"schema_version": "1.0.0", "tasks": {}})


def _load_manifests() -> dict[str, Any]:
    _ensure_state()
    return _read_json(MANIFESTS_FILE, {"schema_version": "1.0.0", "manifests": {}})


def _load_runs() -> dict[str, Any]:
    _ensure_state()
    return _read_json(RUNS_FILE, {"schema_version": "1.0.0", "runs": {}})


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _sha256_tree(path: Path) -> str:
    if path.is_file():
        return _sha256_file(path)
    items: list[dict[str, str]] = []
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        items.append({
            "path": child.relative_to(path).as_posix(),
            "sha256": _sha256_file(child),
        })
    return _sha256_json(items)


def _resolve_scope(relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("ABSOLUTE_SCOPE_NOT_ALLOWED")
    resolved = (PROJECT_ROOT / relative_path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("WORKSPACE_ESCAPE_BLOCKED") from exc
    if not resolved.exists():
        raise ValueError("SCOPE_NOT_FOUND")
    return resolved


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _admission_state() -> dict[str, Any]:
    return _read_json(
        ADMISSION_STATE_FILE,
        {"schema_version": "1.0.0", "tools": {}},
    ).get("tools", {})


def _quality_state() -> tuple[dict[str, Any], dict[str, Any]]:
    baselines = _read_json(
        BASELINES_FILE,
        {"schema_version": "1.0.0", "baselines": {}},
    ).get("baselines", {})
    quarantines = _read_json(
        QUARANTINES_FILE,
        {"schema_version": "1.0.0", "quarantines": {}},
    ).get("quarantines", {})
    return baselines, quarantines


def _scanner_gate(scanner_id: str) -> dict[str, Any]:
    scanner = SCANNERS.get(scanner_id)
    if not scanner:
        raise ValueError("UNKNOWN_SCANNER_ID")

    admission = _admission_state().get(scanner_id)
    baselines, quarantines = _quality_state()

    if scanner_id in quarantines:
        raise ValueError("SCANNER_QUARANTINED")

    if scanner_id == "trivy":
        return {
            "scanner_id": scanner_id,
            "status": "READINESS_HOLD",
            "reason": "OFFLINE_DATABASE_POLICY_REQUIRED",
            "selectable": False,
            "admission_state": admission.get("runtime_state") if admission else None,
            "baseline_id": None,
            "limitations": [
                "Offline database provenance, hash, update, and expiry policy are not approved."
            ],
        }

    if not admission:
        raise ValueError("SCANNER_ADMISSION_STATE_MISSING")
    if admission.get("runtime_state") != scanner["required_admission_state"]:
        raise ValueError(f"SCANNER_ADMISSION_NOT_ELIGIBLE_{admission.get('runtime_state')}")

    baseline = baselines.get(scanner["required_quality_key"])
    if not baseline:
        raise ValueError("SCANNER_QUALITY_BASELINE_REQUIRED")
    if baseline.get("quality_result") not in {"QUALITY_ACCEPTED", "PASS_WITH_LIMITATIONS"}:
        raise ValueError("SCANNER_QUALITY_BASELINE_NOT_ELIGIBLE")

    return {
        "scanner_id": scanner_id,
        "status": (
            "READY_WITH_LIMITATIONS"
            if baseline.get("quality_result") == "PASS_WITH_LIMITATIONS"
            else "READY"
        ),
        "reason": "ADMISSION_AND_QUALITY_GATES_PASSED",
        "selectable": True,
        "admission_state": admission.get("runtime_state"),
        "baseline_id": baseline.get("baseline_id"),
        "quality_result": baseline.get("quality_result"),
        "limitations": baseline.get("limitations", []),
        "version": admission.get("version"),
        "binary_sha256": admission.get("binary_sha256"),
    }


def _scanner_catalog() -> list[dict[str, Any]]:
    result = []
    for scanner_id, scanner in SCANNERS.items():
        try:
            gate = _scanner_gate(scanner_id)
        except ValueError as exc:
            admission = _admission_state().get(scanner_id, {})
            gate = {
                "scanner_id": scanner_id,
                "status": "BLOCKED",
                "reason": str(exc),
                "selectable": False,
                "admission_state": admission.get("runtime_state"),
                "baseline_id": None,
                "limitations": [],
                "version": admission.get("version"),
                "binary_sha256": admission.get("binary_sha256"),
            }
        result.append({**scanner, **gate})
    return result


def _event(event_type: str, entity_id: str, details: dict[str, Any]) -> None:
    _append_jsonl(
        EVIDENCE_FILE,
        {
            "event_id": str(uuid.uuid4()),
            "occurred_at": _utc_now(),
            "event_type": event_type,
            "entity_id": entity_id,
            "details": details,
        },
    )


def _get_task(task_id: str) -> dict[str, Any]:
    task = _load_tasks()["tasks"].get(task_id)
    if not task:
        raise ValueError("TASK_NOT_FOUND")
    return task


def _get_manifest(manifest_id: str) -> dict[str, Any]:
    manifest = _load_manifests()["manifests"].get(manifest_id)
    if not manifest:
        raise ValueError("MANIFEST_NOT_FOUND")
    return manifest


def _get_run(run_id: str) -> dict[str, Any]:
    run = _load_runs()["runs"].get(run_id)
    if not run:
        raise ValueError("RUN_NOT_FOUND")
    return run


def _create_task(request: CreateScanTaskRequest) -> dict[str, Any]:
    if request.scanner_id not in SCANNERS:
        raise ValueError("UNKNOWN_SCANNER_ID")
    if request.scanner_id == "trivy":
        raise ValueError("TRIVY_READINESS_HOLD_OFFLINE_DB_POLICY")

    gate = _scanner_gate(request.scanner_id)
    if not gate["selectable"]:
        raise ValueError("SCANNER_NOT_SELECTABLE")

    scope = _resolve_scope(request.scope_relative)
    rules_path = None
    rules_hash = None
    if SCANNERS[request.scanner_id]["rules_required"]:
        if not request.local_rules_relative:
            raise ValueError("LOCAL_RULES_PATH_REQUIRED")
        rules_path = _resolve_scope(request.local_rules_relative)
        rules_hash = _sha256_tree(rules_path)
    elif request.local_rules_relative:
        raise ValueError("LOCAL_RULES_NOT_ALLOWED_FOR_SCANNER")

    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "title": request.title,
        "purpose": request.purpose,
        "scanner_id": request.scanner_id,
        "scope_relative": _relative(scope),
        "local_rules_relative": _relative(rules_path) if rules_path else None,
        "local_rules_sha256": rules_hash,
        "timeout_seconds": request.timeout_seconds,
        "operator_notes": request.operator_notes,
        "status": "DRAFT",
        "manifest_id": None,
        "run_id": None,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "approval_reference": None,
        "approved_by": None,
    }
    with _LOCK:
        state = _load_tasks()
        state["tasks"][task_id] = task
        _atomic_write_json(TASKS_FILE, state)
    _event("SCAN_TASK_CREATED", task_id, {"scanner_id": request.scanner_id, "status": "DRAFT"})
    return task


def _set_task_status(task_id: str, expected: set[str], new_status: str) -> dict[str, Any]:
    with _LOCK:
        state = _load_tasks()
        task = state["tasks"].get(task_id)
        if not task:
            raise ValueError("TASK_NOT_FOUND")
        if task["status"] not in expected:
            raise ValueError(f"INVALID_TASK_TRANSITION_FROM_{task['status']}")
        task["status"] = new_status
        task["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, state)
    _event("SCAN_TASK_STATUS_CHANGED", task_id, {"status": new_status})
    return task


def _prepare_manifest(task_id: str) -> dict[str, Any]:
    task = _get_task(task_id)
    if task["status"] not in {"DRAFT", "READY_FOR_REVIEW", "RETURNED_FOR_REVIEW"}:
        raise ValueError("TASK_NOT_READY_FOR_MANIFEST")

    gate = _scanner_gate(task["scanner_id"])
    if not gate["selectable"]:
        raise ValueError("SCANNER_NOT_SELECTABLE")

    scope = _resolve_scope(task["scope_relative"])
    rules_path = (
        _resolve_scope(task["local_rules_relative"])
        if task.get("local_rules_relative")
        else None
    )
    if rules_path and _sha256_tree(rules_path) != task["local_rules_sha256"]:
        raise ValueError("LOCAL_RULES_CHANGED_RECREATE_TASK")

    core = {
        "task_id": task_id,
        "scanner_id": task["scanner_id"],
        "scanner_contract_version": SCANNER_CONTRACT_VERSION,
        "quality_baseline_id": gate["baseline_id"],
        "quality_result": gate.get("quality_result"),
        "scanner_version": gate.get("version"),
        "scanner_binary_sha256": gate.get("binary_sha256"),
        "scope_relative": _relative(scope),
        "local_rules_relative": _relative(rules_path) if rules_path else None,
        "local_rules_sha256": task.get("local_rules_sha256"),
        "timeout_seconds": task["timeout_seconds"],
        "network_policy": "blocked",
        "source_write_policy": "blocked",
        "shell_policy": "blocked",
        "git_policy": "blocked",
        "automatic_retry": False,
        "raw_secret_persistence": "blocked",
        "human_result_review": "required",
        "input_sha256": _sha256_json({
            "title": task["title"],
            "purpose": task["purpose"],
            "scanner_id": task["scanner_id"],
            "scope_relative": task["scope_relative"],
            "local_rules_relative": task.get("local_rules_relative"),
            "local_rules_sha256": task.get("local_rules_sha256"),
        }),
    }
    manifest_id = str(uuid.uuid4())
    manifest = {
        "manifest_id": manifest_id,
        **core,
        "manifest_sha256": _sha256_json(core),
        "created_at": _utc_now(),
        "status": "PREPARED",
    }

    with _LOCK:
        manifests = _load_manifests()
        manifests["manifests"][manifest_id] = manifest
        _atomic_write_json(MANIFESTS_FILE, manifests)

        tasks = _load_tasks()
        tasks["tasks"][task_id]["manifest_id"] = manifest_id
        tasks["tasks"][task_id]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)

    _event(
        "SCAN_MANIFEST_PREPARED",
        manifest_id,
        {
            "task_id": task_id,
            "manifest_sha256": manifest["manifest_sha256"],
            "baseline_id": gate["baseline_id"],
        },
    )
    return manifest


def _approve_task(task_id: str, request: ApprovalRequest) -> dict[str, Any]:
    with _LOCK:
        tasks = _load_tasks()
        task = tasks["tasks"].get(task_id)
        if not task:
            raise ValueError("TASK_NOT_FOUND")
        if task["status"] != "READY_FOR_REVIEW":
            raise ValueError("TASK_NOT_READY_FOR_APPROVAL")
        if not task.get("manifest_id"):
            raise ValueError("MANIFEST_REQUIRED")

        manifest = _get_manifest(task["manifest_id"])
        if manifest["status"] != "PREPARED":
            raise ValueError("MANIFEST_NOT_PREPARED")

        task["status"] = "APPROVED_FOR_SCAN"
        task["approval_reference"] = request.approval_reference
        task["approved_by"] = request.approved_by
        task["updated_at"] = _utc_now()
        tasks["tasks"][task_id] = task
        _atomic_write_json(TASKS_FILE, tasks)

        manifests = _load_manifests()
        target = manifests["manifests"][manifest["manifest_id"]]
        target["status"] = "APPROVED"
        target["approval_reference"] = request.approval_reference
        target["approved_by"] = request.approved_by
        target["approved_at"] = _utc_now()
        _atomic_write_json(MANIFESTS_FILE, manifests)

    _event(
        "SCAN_TASK_APPROVED",
        task_id,
        {
            "manifest_id": task["manifest_id"],
            "approval_reference": request.approval_reference,
        },
    )
    return task


def _verify_manifest_current(task: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    gate = _scanner_gate(task["scanner_id"])
    if gate["baseline_id"] != manifest["quality_baseline_id"]:
        raise ValueError("STALE_MANIFEST_BASELINE_CHANGED")
    if gate.get("version") != manifest.get("scanner_version"):
        raise ValueError("STALE_MANIFEST_SCANNER_VERSION_CHANGED")
    if gate.get("binary_sha256") != manifest.get("scanner_binary_sha256"):
        raise ValueError("STALE_MANIFEST_SCANNER_HASH_CHANGED")
    if manifest["scanner_contract_version"] != SCANNER_CONTRACT_VERSION:
        raise ValueError("STALE_MANIFEST_CONTRACT_CHANGED")

    rules_path = (
        _resolve_scope(task["local_rules_relative"])
        if task.get("local_rules_relative")
        else None
    )
    if rules_path and _sha256_tree(rules_path) != manifest.get("local_rules_sha256"):
        raise ValueError("STALE_MANIFEST_LOCAL_RULES_CHANGED")
    return gate


def _wave1_module():
    return importlib.import_module(
        "palwakf_local_agents.open_source_tools_operational_admission_wave1_v1"
    )


def _sanitize_report(report: dict[str, Any]) -> dict[str, Any]:
    excerpt = str(report.get("redacted_output_excerpt") or "")[:MAX_RESULT_EXCERPT]
    return {
        "invocation_id": report.get("invocation_id"),
        "tool_id": report.get("tool_id"),
        "tool_version": report.get("tool_version"),
        "executable_name": report.get("executable_name"),
        "executable_sha256": report.get("executable_sha256"),
        "scope_relative": report.get("scope_relative"),
        "duration_ms": report.get("duration_ms"),
        "timed_out": report.get("timed_out"),
        "exit_code": report.get("exit_code"),
        "exit_class": report.get("exit_class"),
        "result": report.get("result"),
        "redaction_applied": bool(report.get("redaction_applied")),
        "truncated": bool(report.get("truncated")),
        "output_sha256": report.get("output_sha256"),
        "redacted_output_excerpt": excerpt,
        "raw_output_persisted": False,
        "source_write": "blocked",
        "network_runtime": "blocked",
        "human_trigger_required": True,
    }


def _run_task(task_id: str) -> dict[str, Any]:
    task = _get_task(task_id)
    if task["status"] != "APPROVED_FOR_SCAN":
        raise ValueError("UNAPPROVED_SCAN_EXECUTION_BLOCKED")

    manifest = _get_manifest(task["manifest_id"])
    if manifest["status"] != "APPROVED":
        raise ValueError("UNAPPROVED_MANIFEST_EXECUTION_BLOCKED")

    _verify_manifest_current(task, manifest)

    run_id = str(uuid.uuid4())
    with _LOCK:
        tasks = _load_tasks()
        tasks["tasks"][task_id]["status"] = "RUNNING"
        tasks["tasks"][task_id]["run_id"] = run_id
        tasks["tasks"][task_id]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)

    _event(
        "PROJECT_SCOPED_SCAN_STARTED",
        run_id,
        {
            "task_id": task_id,
            "manifest_id": manifest["manifest_id"],
            "scanner_id": task["scanner_id"],
        },
    )

    started_at = _utc_now()
    started = time.monotonic()
    try:
        wave1 = _wave1_module()
        request = wave1.ControlledScanRequest(
            scope_relative=task["scope_relative"],
            local_rules_relative=task.get("local_rules_relative"),
            timeout_seconds=task["timeout_seconds"],
        )
        report = wave1._run_controlled_scan(task["scanner_id"], request)
        safe_report = _sanitize_report(report)

        run = {
            "run_id": run_id,
            "task_id": task_id,
            "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "scanner_id": task["scanner_id"],
            "status": "HUMAN_RESULT_REVIEW",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "report": safe_report,
            "result_sha256": _sha256_json(safe_report),
            "source_write": "none",
            "network_runtime": "none",
            "shell": "none",
            "git": "none",
            "automatic_retry": False,
        }

        with _LOCK:
            runs = _load_runs()
            runs["runs"][run_id] = run
            _atomic_write_json(RUNS_FILE, runs)

            tasks = _load_tasks()
            tasks["tasks"][task_id]["status"] = "HUMAN_RESULT_REVIEW"
            tasks["tasks"][task_id]["updated_at"] = _utc_now()
            _atomic_write_json(TASKS_FILE, tasks)

        _event(
            "PROJECT_SCOPED_SCAN_COMPLETED",
            run_id,
            {
                "task_id": task_id,
                "result_sha256": run["result_sha256"],
                "redaction_applied": safe_report["redaction_applied"],
                "timed_out": safe_report["timed_out"],
                "exit_class": safe_report["exit_class"],
            },
        )
        return run
    except Exception as exc:
        with _LOCK:
            tasks = _load_tasks()
            tasks["tasks"][task_id]["status"] = "FAILED"
            tasks["tasks"][task_id]["updated_at"] = _utc_now()
            _atomic_write_json(TASKS_FILE, tasks)
        _event(
            "PROJECT_SCOPED_SCAN_FAILED",
            run_id,
            {
                "task_id": task_id,
                "error_class": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise


def _review_result(run_id: str, request: ResultReviewRequest) -> dict[str, Any]:
    run = _get_run(run_id)
    if run["status"] != "HUMAN_RESULT_REVIEW":
        raise ValueError("RUN_NOT_READY_FOR_RESULT_REVIEW")

    status_map = {
        "ACCEPT": "ACCEPTED_RESULT",
        "RETURN": "RETURNED_FOR_REVIEW",
        "REJECT": "REJECTED_RESULT",
    }
    new_status = status_map[request.decision]
    review = {
        "review_id": str(uuid.uuid4()),
        "run_id": run_id,
        "task_id": run["task_id"],
        "decision": request.decision,
        "notes": request.notes,
        "reviewed_by": request.reviewed_by,
        "reviewed_at": _utc_now(),
    }

    with _LOCK:
        runs = _load_runs()
        runs["runs"][run_id]["status"] = new_status
        runs["runs"][run_id]["review"] = review
        _atomic_write_json(RUNS_FILE, runs)

        tasks = _load_tasks()
        tasks["tasks"][run["task_id"]]["status"] = new_status
        tasks["tasks"][run["task_id"]]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)

        if request.decision == "ACCEPT":
            checkpoints = _read_json(
                CHECKPOINTS_FILE,
                {"schema_version": "1.0.0", "checkpoints": {}},
            )
            checkpoint_id = str(uuid.uuid4())
            checkpoints["checkpoints"][checkpoint_id] = {
                "checkpoint_id": checkpoint_id,
                "task_id": run["task_id"],
                "run_id": run_id,
                "scanner_id": run["scanner_id"],
                "manifest_sha256": run["manifest_sha256"],
                "result_sha256": run["result_sha256"],
                "created_at": _utc_now(),
                "snapshot_type": "scan_metadata_only",
                "raw_findings_snapshot": False,
            }
            _atomic_write_json(CHECKPOINTS_FILE, checkpoints)
            review["checkpoint_id"] = checkpoint_id

    _append_jsonl(REVIEWS_FILE, review)
    _event(
        "PROJECT_SCOPED_SCAN_REVIEWED",
        run_id,
        {
            "decision": request.decision,
            "reviewed_by": request.reviewed_by,
        },
    )
    return review


def _dashboard() -> dict[str, Any]:
    tasks = list(_load_tasks()["tasks"].values())
    runs = list(_load_runs()["runs"].values())
    scanners = _scanner_catalog()
    return {
        "result": "PASS",
        "summary": {
            "drafts": sum(1 for item in tasks if item["status"] == "DRAFT"),
            "ready_for_review": sum(1 for item in tasks if item["status"] == "READY_FOR_REVIEW"),
            "approved": sum(1 for item in tasks if item["status"] == "APPROVED_FOR_SCAN"),
            "result_review": sum(1 for item in tasks if item["status"] == "HUMAN_RESULT_REVIEW"),
            "accepted_results": sum(1 for item in tasks if item["status"] == "ACCEPTED_RESULT"),
            "ready_scanners": sum(1 for item in scanners if item["selectable"]),
        },
        "tasks": sorted(tasks, key=lambda item: item["updated_at"], reverse=True)[:50],
        "runs": sorted(runs, key=lambda item: item["completed_at"], reverse=True)[:30],
        "scanners": scanners,
    }


def _http_error(exc: Exception) -> HTTPException:
    message = str(exc)
    status = 404 if message.endswith("_NOT_FOUND") else 409
    if any(token in message for token in ["BLOCKED", "REQUIRED", "NOT_ELIGIBLE", "HOLD", "QUARANTINED", "STALE"]):
        status = 403
    return HTTPException(status_code=status, detail=message)


@router.get("/api/v1/operational-core/external-scanners-wave2/health")
def health() -> dict[str, Any]:
    _ensure_state()
    return {
        "result": "PASS",
        "mode": "quality_gated_project_scoped_external_scanners",
        "scanner_count": len(SCANNERS),
        "semgrep": "quality_and_admission_gated",
        "gitleaks": "quality_and_admission_gated",
        "trivy": "readiness_hold",
        "model_inference": "none",
        "shell": "blocked",
        "git": "blocked",
        "network_runtime": "blocked",
        "source_write": "blocked",
        "automatic_retry": "blocked",
        "human_approval": "required",
        "human_result_review": "required",
    }


@router.get("/api/v1/operational-core/external-scanners-wave2/dashboard")
def dashboard() -> dict[str, Any]:
    return _dashboard()


@router.get("/api/v1/operational-core/external-scanners-wave2/scanners")
def scanners() -> dict[str, Any]:
    return {"result": "PASS", "scanners": _scanner_catalog()}


@router.get("/api/v1/operational-core/external-scanners-wave2/tasks")
def tasks() -> dict[str, Any]:
    return _load_tasks()


@router.get("/api/v1/operational-core/external-scanners-wave2/manifests")
def manifests() -> dict[str, Any]:
    return _load_manifests()


@router.get("/api/v1/operational-core/external-scanners-wave2/runs")
def runs() -> dict[str, Any]:
    return _load_runs()


@router.get("/api/v1/operational-core/external-scanners-wave2/evidence")
def evidence(limit: int = 200) -> dict[str, Any]:
    if not EVIDENCE_FILE.is_file():
        return {"result": "PASS", "events": []}
    lines = EVIDENCE_FILE.read_text(encoding="utf-8").splitlines()
    safe_limit = max(1, min(limit, 500))
    return {
        "result": "PASS",
        "events": [json.loads(line) for line in lines[-safe_limit:] if line.strip()],
    }


@router.get("/api/v1/operational-core/external-scanners-wave2/checkpoints")
def checkpoints() -> dict[str, Any]:
    _ensure_state()
    return _read_json(
        CHECKPOINTS_FILE,
        {"schema_version": "1.0.0", "checkpoints": {}},
    )


@router.get("/api/v1/operational-core/external-scanners-wave2/governance")
def governance() -> dict[str, Any]:
    return {
        "result": "PASS",
        "state_machine": [
            "DRAFT",
            "READY_FOR_REVIEW",
            "APPROVED_FOR_SCAN",
            "RUNNING",
            "HUMAN_RESULT_REVIEW",
            "ACCEPTED_RESULT",
            "RETURNED_FOR_REVIEW",
            "REJECTED_RESULT",
            "FAILED",
        ],
        "boundaries": health(),
        "scanner_contracts": SCANNERS,
        "governance_pages": [
            "/agent-console/security-scans/governance",
            "/agent-console/security-scans/manifests",
            "/agent-console/security-scans/evidence",
        ],
    }


@router.post("/api/v1/operational-core/external-scanners-wave2/tasks")
def create_task(request: CreateScanTaskRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "task": _create_task(request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/external-scanners-wave2/tasks/{task_id}/submit")
def submit_task(task_id: str) -> dict[str, Any]:
    try:
        return {
            "result": "PASS",
            "task": _set_task_status(
                task_id,
                {"DRAFT", "RETURNED_FOR_REVIEW"},
                "READY_FOR_REVIEW",
            ),
        }
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/external-scanners-wave2/tasks/{task_id}/prepare-manifest")
def prepare_manifest(task_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "manifest": _prepare_manifest(task_id)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/external-scanners-wave2/tasks/{task_id}/approve")
def approve_task(task_id: str, request: ApprovalRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "task": _approve_task(task_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/external-scanners-wave2/tasks/{task_id}/run")
def run_task(task_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "run": _run_task(task_id)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/external-scanners-wave2/runs/{run_id}/review")
def review_result(run_id: str, request: ResultReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "review": _review_result(run_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc
