from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["open-source-tools-operational-admission-wave1-v1"])

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_FILE = MODULE_DIR / "open_source_capability_registry_v1.json"
ADAPTERS_FILE = MODULE_DIR / "open_source_adapter_contracts_v1.json"
RUNTIME_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "open_source_tools_wave1"
STATE_FILE = RUNTIME_ROOT / "tool_admission_wave1_state.json"
EVENTS_FILE = RUNTIME_ROOT / "tool_admission_wave1_events.jsonl"
REPORTS_FILE = RUNTIME_ROOT / "tool_admission_wave1_reports.json"
TELEMETRY_FILE = RUNTIME_ROOT / "tool_admission_wave1_telemetry.jsonl"
TEMP_ROOT = RUNTIME_ROOT / "temp"

_LOCK = threading.RLock()
MAX_OUTPUT_BYTES = 262_144
DEFAULT_TIMEOUT_SECONDS = 20
MAX_SCAN_TIMEOUT_SECONDS = 180

WAVE1_TOOL_IDS = {"tree_sitter", "opentelemetry", "semgrep", "gitleaks", "trivy"}
DEFERRED_TOOL_IDS = {"temporal", "prefect", "langfuse", "phoenix", "swe_agent", "aider"}

EXECUTABLE_CANDIDATES: dict[str, list[str]] = {
    "tree_sitter": ["tree-sitter"],
    "opentelemetry": ["otelcol", "otelcol-contrib"],
    "semgrep": ["semgrep"],
    "gitleaks": ["gitleaks"],
    "trivy": ["trivy"],
    "temporal": ["temporal"],
    "prefect": ["prefect"],
    "langfuse": [],
    "phoenix": ["phoenix"],
    "swe_agent": ["sweagent", "swe-agent"],
    "aider": ["aider"],
}

VERSION_ARGV: dict[str, list[str]] = {
    "tree_sitter": ["--version"],
    "semgrep": ["--version"],
    "gitleaks": ["version"],
    "trivy": ["--version"],
    "temporal": ["--version"],
    "prefect": ["version"],
    "phoenix": ["--version"],
    "swe_agent": ["--version"],
    "aider": ["--version"],
}

TARGET_STATE_WHEN_PRESENT: dict[str, str] = {
    "tree_sitter": "CONTROLLED_ACTIVE_READ_ONLY",
    "opentelemetry": "CONTROLLED_ACTIVE_LOCAL_ONLY",
    "semgrep": "CONTROLLED_USER_TRIGGERED_SCAN",
    "gitleaks": "CONTROLLED_USER_TRIGGERED_SCAN",
    "trivy": "READINESS_HOLD_OFFLINE_DB_POLICY",
}

DEFERRED_STATES: dict[str, str] = {
    "temporal": "ARCHITECTURE_DEFERRED",
    "prefect": "ARCHITECTURE_DEFERRED",
    "langfuse": "PRIVACY_AND_LICENSE_REVIEW",
    "phoenix": "LICENSE_AND_PRIVACY_REVIEW",
    "swe_agent": "BLOCKED_CURRENT_PHASE",
    "aider": "BLOCKED_CURRENT_PHASE",
}


class ProbeRequest(BaseModel):
    tool_ids: list[str] | None = None


class ControlledScanRequest(BaseModel):
    scope_relative: str = "."
    local_rules_relative: str | None = None
    timeout_seconds: int = Field(default=120, ge=5, le=MAX_SCAN_TIMEOUT_SECONDS)


class SuspendRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_runtime() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, value: Any) -> None:
    _ensure_runtime()
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        temp_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    _ensure_runtime()
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_registry() -> dict[str, Any]:
    if not REGISTRY_FILE.is_file():
        raise RuntimeError("OPEN_SOURCE_CAPABILITY_REGISTRY_V1_NOT_FOUND")
    return _read_json(REGISTRY_FILE, {})


def _load_adapters() -> dict[str, Any]:
    if not ADAPTERS_FILE.is_file():
        raise RuntimeError("OPEN_SOURCE_ADAPTER_CONTRACTS_V1_NOT_FOUND")
    return _read_json(ADAPTERS_FILE, {})


def _registry_map() -> dict[str, dict[str, Any]]:
    registry = _load_registry()
    return {item["id"]: item for item in registry.get("capabilities", [])}


def _initial_tool_record(item: dict[str, Any]) -> dict[str, Any]:
    tool_id = item["id"]
    initial_state = DEFERRED_STATES.get(tool_id, "REGISTERED_AWAITING_PROBE")
    return {
        "tool_id": tool_id,
        "name": item.get("name", tool_id),
        "registry_decision": item.get("decision"),
        "runtime_state": initial_state,
        "present": False,
        "detected_executable_name": None,
        "version": None,
        "binary_sha256": None,
        "last_probe_at": None,
        "last_probe_result": "NOT_PROBED",
        "last_invocation_at": None,
        "last_invocation_result": None,
        "suspended": False,
        "suspension_reason": None,
        "allowed_operations": _allowed_operations(tool_id, initial_state),
    }


def _allowed_operations(tool_id: str, runtime_state: str) -> list[str]:
    if runtime_state == "CONTROLLED_ACTIVE_READ_ONLY":
        return ["version_probe", "read_only_parser_readiness"]
    if runtime_state == "CONTROLLED_ACTIVE_LOCAL_ONLY":
        return ["version_probe", "local_telemetry_status"]
    if runtime_state == "CONTROLLED_USER_TRIGGERED_SCAN":
        return ["version_probe", "controlled_read_only_scan"]
    if runtime_state == "READINESS_HOLD_OFFLINE_DB_POLICY":
        return ["version_probe", "offline_database_readiness"]
    if tool_id in DEFERRED_TOOL_IDS:
        return ["presence_probe_only"]
    return ["presence_probe", "version_probe_if_supported"]


def _ensure_state() -> dict[str, Any]:
    with _LOCK:
        registry = _load_registry()
        capabilities = registry.get("capabilities", [])
        current = _read_json(STATE_FILE, None)
        if not isinstance(current, dict):
            current = {
                "schema_version": "1.0.0",
                "mode": "operational_admission_and_controlled_runtime_wave1",
                "created_at": _utc_now(),
                "updated_at": _utc_now(),
                "tools": {},
                "boundaries": _boundaries(),
            }

        tools = current.setdefault("tools", {})
        for item in capabilities:
            if item["id"] not in tools:
                tools[item["id"]] = _initial_tool_record(item)

        current["updated_at"] = _utc_now()
        current["boundaries"] = _boundaries()
        _atomic_write_json(STATE_FILE, current)
        if not REPORTS_FILE.exists():
            _atomic_write_json(REPORTS_FILE, {"schema_version": "1.0.0", "reports": []})
        return current


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _utc_now()
    _atomic_write_json(STATE_FILE, state)


def _event(event_type: str, tool_id: str | None, details: dict[str, Any]) -> str:
    event_id = str(uuid.uuid4())
    record = {
        "event_id": event_id,
        "occurred_at": _utc_now(),
        "event_type": event_type,
        "tool_id": tool_id,
        "details": details,
    }
    _append_jsonl(EVENTS_FILE, record)
    _append_jsonl(
        TELEMETRY_FILE,
        {
            "trace_id": event_id.replace("-", ""),
            "timestamp": record["occurred_at"],
            "name": f"local_agents.open_source_tools.{event_type.lower()}",
            "status": details.get("result", "RECORDED"),
            "attributes": {
                "tool_id": tool_id,
                "execution_mode": details.get("execution_mode"),
                "exit_class": details.get("exit_class"),
                "redaction_applied": details.get("redaction_applied"),
            },
            "content_policy": "no_prompt_no_source_no_secret",
            "export": "local_jsonl_only",
        },
    )
    return event_id


def _boundaries() -> dict[str, str]:
    return {
        "auto_install": "blocked",
        "auto_download": "blocked",
        "shell": "blocked",
        "git": "blocked",
        "model_inference": "none",
        "self_apply": "blocked",
        "autofix": "blocked",
        "remote_rules": "blocked",
        "network_runtime": "blocked_by_default",
        "source_write": "blocked",
        "arbitrary_arguments": "blocked",
        "automatic_retry": "blocked",
        "runtime_write_scope": "runtime_state/operational_core_v1/open_source_tools_wave1_only",
    }


def _sanitized_environment() -> dict[str, str]:
    allowed_keys = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "LOCALAPPDATA",
        "APPDATA",
        "PROGRAMDATA",
        "LANG",
        "LC_ALL",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed_keys}
    env.update(
        {
            "NO_COLOR": "1",
            "SEMGREP_SEND_METRICS": "off",
            "SEMGREP_ENABLE_VERSION_CHECK": "0",
            "TRIVY_DISABLE_VEX_NOTICE": "true",
            "TRIVY_NO_PROGRESS": "true",
        }
    )
    for key in list(env):
        if key.upper().endswith("_PROXY") or key.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}:
            env.pop(key, None)
    return env


def _redact(text: str) -> tuple[str, bool]:
    original = text
    text = text.replace(str(PROJECT_ROOT), "<WORKSPACE>")
    text = text.replace(str(PROJECT_ROOT).replace("\\", "/"), "<WORKSPACE>")

    patterns = [
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "<REDACTED_PRIVATE_KEY>"),
        (r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*['\"]?[^'\"\s,;]+", r"\1=<REDACTED>"),
        (r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{12,}", r"\1 <REDACTED>"),
        (r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{12,}\b", "<REDACTED_TOKEN>"),
        (r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s\"']+", "<REDACTED_CONNECTION_STRING>"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)

    return text, text != original


def _resolve_executable(tool_id: str) -> tuple[str | None, str | None]:
    for candidate in EXECUTABLE_CANDIDATES.get(tool_id, []):
        resolved = shutil.which(candidate)
        if not resolved:
            continue
        path = Path(resolved)
        # Direct argv only. Windows command wrappers require a shell and are not admitted.
        if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat", ".ps1"}:
            continue
        return str(path), path.name
    return None, None


def _run_direct_argv(
    *,
    executable_path: str,
    argv_tail: list[str],
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    argv = [executable_path, *argv_tail]
    try:
        completed = subprocess.run(
            argv,
            cwd=str(cwd),
            env=_sanitized_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
        exit_code = int(completed.returncode)
        stdout_bytes = completed.stdout[:MAX_OUTPUT_BYTES]
        stderr_bytes = completed.stderr[:MAX_OUTPUT_BYTES]
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        truncated = len(completed.stdout) > MAX_OUTPUT_BYTES or len(completed.stderr) > MAX_OUTPUT_BYTES
        return {
            "result": "PASS" if exit_code == 0 else "PROCESS_NONZERO",
            "exit_code": exit_code,
            "exit_class": "ZERO" if exit_code == 0 else "NONZERO",
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated,
            "timed_out": False,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "execution_mode": "direct_argv_shell_false",
        }
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"")
        stderr = (exc.stderr or b"")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "result": "TIMEOUT",
            "exit_code": None,
            "exit_class": "TIMEOUT",
            "stdout": str(stdout)[:MAX_OUTPUT_BYTES],
            "stderr": str(stderr)[:MAX_OUTPUT_BYTES],
            "truncated": False,
            "timed_out": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "execution_mode": "direct_argv_shell_false",
        }


def _probe_opentelemetry() -> dict[str, Any]:
    package_candidates = [
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-distro",
    ]
    detected = []
    for name in package_candidates:
        try:
            detected.append({"package": name, "version": importlib.metadata.version(name)})
        except importlib.metadata.PackageNotFoundError:
            pass

    if detected:
        version = ", ".join(f"{item['package']}={item['version']}" for item in detected)
        return {
            "present": True,
            "detected_executable_name": None,
            "version": version,
            "binary_sha256": None,
            "probe_result": "PASS",
            "execution_mode": "python_distribution_metadata_no_process",
            "redaction_applied": False,
            "exit_class": "NOT_APPLICABLE",
        }

    executable_path, executable_name = _resolve_executable("opentelemetry")
    if not executable_path:
        return {
            "present": False,
            "detected_executable_name": None,
            "version": None,
            "binary_sha256": None,
            "probe_result": "MISSING",
            "execution_mode": "presence_only",
            "redaction_applied": False,
            "exit_class": "NOT_RUN",
        }

    run = _run_direct_argv(
        executable_path=executable_path,
        argv_tail=["--version"],
        cwd=PROJECT_ROOT,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    output, redacted = _redact((run["stdout"] + "\n" + run["stderr"]).strip())
    return {
        "present": True,
        "detected_executable_name": executable_name,
        "version": output.splitlines()[0][:300] if output else None,
        "binary_sha256": _sha256_file(Path(executable_path)),
        "probe_result": run["result"],
        "execution_mode": run["execution_mode"],
        "redaction_applied": redacted,
        "exit_class": run["exit_class"],
    }


def _probe_tool(tool_id: str) -> dict[str, Any]:
    registry = _registry_map()
    if tool_id not in registry:
        raise ValueError("UNKNOWN_TOOL_ID")

    if tool_id == "opentelemetry":
        return _probe_opentelemetry()

    executable_path, executable_name = _resolve_executable(tool_id)
    if not executable_path:
        return {
            "present": False,
            "detected_executable_name": None,
            "version": None,
            "binary_sha256": None,
            "probe_result": "MISSING",
            "execution_mode": "presence_only",
            "redaction_applied": False,
            "exit_class": "NOT_RUN",
        }

    version_args = VERSION_ARGV.get(tool_id)
    if not version_args:
        return {
            "present": True,
            "detected_executable_name": executable_name,
            "version": None,
            "binary_sha256": _sha256_file(Path(executable_path)),
            "probe_result": "PRESENT_VERSION_NOT_PROBED",
            "execution_mode": "presence_and_hash_only",
            "redaction_applied": False,
            "exit_class": "NOT_RUN",
        }

    run = _run_direct_argv(
        executable_path=executable_path,
        argv_tail=version_args,
        cwd=PROJECT_ROOT,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    combined, redacted = _redact((run["stdout"] + "\n" + run["stderr"]).strip())
    return {
        "present": True,
        "detected_executable_name": executable_name,
        "version": combined.splitlines()[0][:300] if combined else None,
        "binary_sha256": _sha256_file(Path(executable_path)),
        "probe_result": run["result"],
        "execution_mode": run["execution_mode"],
        "redaction_applied": redacted,
        "exit_class": run["exit_class"],
    }


def _state_after_probe(tool_id: str, probe: dict[str, Any], previous: dict[str, Any]) -> str:
    if previous.get("suspended"):
        return "SUSPENDED"
    if tool_id in DEFERRED_TOOL_IDS:
        return DEFERRED_STATES[tool_id]
    if not probe["present"]:
        return "MISSING_NOT_FAILED"
    if probe["probe_result"] not in {"PASS", "PRESENT_VERSION_NOT_PROBED"}:
        return "VERSION_PROBE_HOLD"
    return TARGET_STATE_WHEN_PRESENT.get(tool_id, "REGISTERED")


def _apply_probe(tool_id: str) -> dict[str, Any]:
    with _LOCK:
        state = _ensure_state()
        previous = state["tools"][tool_id]
        probe = _probe_tool(tool_id)
        runtime_state = _state_after_probe(tool_id, probe, previous)
        previous.update(
            {
                "runtime_state": runtime_state,
                "present": probe["present"],
                "detected_executable_name": probe["detected_executable_name"],
                "version": probe["version"],
                "binary_sha256": probe["binary_sha256"],
                "last_probe_at": _utc_now(),
                "last_probe_result": probe["probe_result"],
                "allowed_operations": _allowed_operations(tool_id, runtime_state),
            }
        )
        _save_state(state)
        _event(
            "TOOL_PROBE",
            tool_id,
            {
                "result": probe["probe_result"],
                "runtime_state": runtime_state,
                "execution_mode": probe["execution_mode"],
                "exit_class": probe["exit_class"],
                "redaction_applied": probe["redaction_applied"],
                "present": probe["present"],
            },
        )
        return previous


def _resolve_scope(relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("ABSOLUTE_SCOPE_NOT_ALLOWED")
    resolved = (PROJECT_ROOT / relative_path).resolve()
    project_resolved = PROJECT_ROOT.resolve()
    try:
        resolved.relative_to(project_resolved)
    except ValueError as exc:
        raise ValueError("WORKSPACE_ESCAPE_BLOCKED") from exc
    if not resolved.exists():
        raise ValueError("SCOPE_NOT_FOUND")
    return resolved


def _resolve_local_rules(relative: str | None) -> Path:
    if not relative:
        raise ValueError("LOCAL_RULES_PATH_REQUIRED")
    path = _resolve_scope(relative)
    if not path.is_file() and not path.is_dir():
        raise ValueError("LOCAL_RULES_NOT_FILE_OR_DIRECTORY")
    return path


def _current_executable_or_block(tool_id: str, record: dict[str, Any]) -> tuple[str, str]:
    executable_path, executable_name = _resolve_executable(tool_id)
    if not executable_path or not executable_name:
        raise ValueError("EXECUTABLE_MISSING")
    current_hash = _sha256_file(Path(executable_path))
    expected_hash = record.get("binary_sha256")
    if not expected_hash:
        raise ValueError("BINARY_HASH_NOT_ESTABLISHED")
    if current_hash != expected_hash:
        raise ValueError("BINARY_HASH_CHANGED_SUSPEND_REQUIRED")
    return executable_path, executable_name


def _build_scan_command(tool_id: str, executable_path: str, scope: Path, rules: Path | None, report_path: Path) -> list[str]:
    if tool_id == "semgrep":
        if rules is None:
            raise ValueError("LOCAL_RULES_PATH_REQUIRED")
        return [
            executable_path,
            "scan",
            "--config",
            str(rules),
            "--json",
            "--metrics=off",
            str(scope),
        ]
    if tool_id == "gitleaks":
        return [
            executable_path,
            "dir",
            str(scope),
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
            "--redact=100",
            "--no-color",
            "--exit-code",
            "0",
        ]
    if tool_id == "trivy":
        return [
            executable_path,
            "fs",
            "--format",
            "json",
            "--quiet",
            "--skip-db-update",
            "--skip-java-db-update",
            "--skip-check-update",
            "--offline-scan",
            str(scope),
        ]
    raise ValueError("CONTROLLED_SCAN_NOT_SUPPORTED")


def _save_report(report: dict[str, Any]) -> None:
    with _LOCK:
        current = _read_json(REPORTS_FILE, {"schema_version": "1.0.0", "reports": []})
        reports = current.setdefault("reports", [])
        reports.append(report)
        if len(reports) > 100:
            del reports[:-100]
        _atomic_write_json(REPORTS_FILE, current)


def _run_controlled_scan(tool_id: str, request: ControlledScanRequest) -> dict[str, Any]:
    if tool_id not in {"semgrep", "gitleaks", "trivy"}:
        raise ValueError("CONTROLLED_SCAN_NOT_SUPPORTED")

    with _LOCK:
        state = _ensure_state()
        record = state["tools"].get(tool_id)
        if not record:
            raise ValueError("UNKNOWN_TOOL_ID")
        if record.get("suspended"):
            raise ValueError("TOOL_SUSPENDED")
        allowed_states = {"CONTROLLED_USER_TRIGGERED_SCAN"}
        if tool_id == "trivy":
            # Trivy remains held until the offline DB policy is explicitly satisfied.
            raise ValueError("TRIVY_READINESS_HOLD_OFFLINE_DB_POLICY")
        if record.get("runtime_state") not in allowed_states:
            raise ValueError("TOOL_NOT_ADMITTED_FOR_CONTROLLED_SCAN")

    scope = _resolve_scope(request.scope_relative)
    rules = _resolve_local_rules(request.local_rules_relative) if tool_id == "semgrep" else None
    executable_path, executable_name = _current_executable_or_block(tool_id, record)

    invocation_id = str(uuid.uuid4())
    raw_report_path = TEMP_ROOT / f"{invocation_id}.json"
    argv = _build_scan_command(tool_id, executable_path, scope, rules, raw_report_path)
    argv_tail = argv[1:]

    run = _run_direct_argv(
        executable_path=executable_path,
        argv_tail=argv_tail,
        cwd=PROJECT_ROOT,
        timeout_seconds=request.timeout_seconds,
    )

    raw_output = run["stdout"]
    if raw_report_path.is_file():
        try:
            raw_output += "\n" + raw_report_path.read_text(encoding="utf-8", errors="replace")
        finally:
            raw_report_path.unlink(missing_ok=True)

    redacted_output, redaction_applied = _redact(raw_output + "\n" + run["stderr"])
    output_hash = hashlib.sha256(redacted_output.encode("utf-8")).hexdigest().upper()

    report = {
        "invocation_id": invocation_id,
        "tool_id": tool_id,
        "tool_version": record.get("version"),
        "executable_name": executable_name,
        "executable_sha256": record.get("binary_sha256"),
        "scope_relative": str(scope.relative_to(PROJECT_ROOT)).replace("\\", "/") or ".",
        "started_and_completed_at": _utc_now(),
        "duration_ms": run["duration_ms"],
        "timeout_seconds": request.timeout_seconds,
        "timed_out": run["timed_out"],
        "exit_code": run["exit_code"],
        "exit_class": run["exit_class"],
        "result": run["result"],
        "redaction_applied": redaction_applied,
        "truncated": run["truncated"],
        "output_sha256": output_hash,
        "redacted_output_excerpt": redacted_output[:65_536],
        "raw_output_persisted": False,
        "network_runtime": "blocked_by_command_profile_and_sanitized_environment",
        "source_write": "blocked_by_contract",
        "human_trigger_required": True,
    }
    _save_report(report)

    with _LOCK:
        state = _ensure_state()
        record = state["tools"][tool_id]
        record["last_invocation_at"] = report["started_and_completed_at"]
        record["last_invocation_result"] = report["result"]
        if run["timed_out"]:
            record["runtime_state"] = "SUSPENDED_TIMEOUT_REVIEW"
            record["suspended"] = True
            record["suspension_reason"] = "Controlled scan exceeded timeout."
        _save_state(state)

    _event(
        "CONTROLLED_SCAN",
        tool_id,
        {
            "result": report["result"],
            "execution_mode": run["execution_mode"],
            "exit_class": report["exit_class"],
            "redaction_applied": redaction_applied,
            "output_sha256": output_hash,
            "scope_relative": report["scope_relative"],
        },
    )
    return report


def _http_error(exc: Exception) -> HTTPException:
    message = str(exc)
    status = 404 if message in {"UNKNOWN_TOOL_ID", "SCOPE_NOT_FOUND", "EXECUTABLE_MISSING"} else 409
    if "BLOCKED" in message or "NOT_ADMITTED" in message or "HOLD" in message or "SUSPENDED" in message:
        status = 403
    return HTTPException(status_code=status, detail=message)


@router.get("/api/v1/operational-core/open-source-tools-wave1/health")
def health() -> dict[str, Any]:
    state = _ensure_state()
    return {
        "result": "PASS",
        "mode": state["mode"],
        "tool_count": len(state["tools"]),
        "wave1_tool_count": len(WAVE1_TOOL_IDS),
        "deferred_tool_count": len(DEFERRED_TOOL_IDS),
        "safe_process_broker": "direct_argv_shell_false",
        "automatic_install": "blocked",
        "automatic_download": "blocked",
        "model_inference": "none",
    }


@router.get("/api/v1/operational-core/open-source-tools-wave1/state")
def state() -> dict[str, Any]:
    return _ensure_state()


@router.post("/api/v1/operational-core/open-source-tools-wave1/probe")
def probe(request: ProbeRequest) -> dict[str, Any]:
    registry = _registry_map()
    requested = request.tool_ids or list(registry)
    unknown = sorted(set(requested) - set(registry))
    if unknown:
        raise HTTPException(status_code=404, detail=f"UNKNOWN_TOOL_IDS={unknown}")
    results = []
    for tool_id in requested:
        try:
            results.append(_apply_probe(tool_id))
        except Exception as exc:
            raise _http_error(exc) from exc
    return {"result": "PASS", "probed": results, "automatic_activation": False}


@router.post("/api/v1/operational-core/open-source-tools-wave1/tools/{tool_id}/probe")
def probe_one(tool_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "tool": _apply_probe(tool_id)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/open-source-tools-wave1/tools/{tool_id}/scan")
def controlled_scan(tool_id: str, request: ControlledScanRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "report": _run_controlled_scan(tool_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/api/v1/operational-core/open-source-tools-wave1/tools/{tool_id}/suspend")
def suspend(tool_id: str, request: SuspendRequest) -> dict[str, Any]:
    with _LOCK:
        state = _ensure_state()
        record = state["tools"].get(tool_id)
        if not record:
            raise HTTPException(status_code=404, detail="UNKNOWN_TOOL_ID")
        record["suspended"] = True
        record["suspension_reason"] = request.reason
        record["runtime_state"] = "SUSPENDED"
        record["allowed_operations"] = ["presence_probe_only"]
        _save_state(state)
        _event("TOOL_SUSPENDED", tool_id, {"result": "PASS", "reason": request.reason})
        return {"result": "PASS", "tool": record}


@router.get("/api/v1/operational-core/open-source-tools-wave1/events")
def events(limit: int = 100) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 500))
    if not EVENTS_FILE.is_file():
        return {"result": "PASS", "events": []}
    lines = EVENTS_FILE.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in lines[-safe_limit:] if line.strip()]
    return {"result": "PASS", "events": parsed}


@router.get("/api/v1/operational-core/open-source-tools-wave1/reports")
def reports(limit: int = 30) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    current = _read_json(REPORTS_FILE, {"schema_version": "1.0.0", "reports": []})
    return {"result": "PASS", "reports": current.get("reports", [])[-safe_limit:]}


@router.get("/api/v1/operational-core/open-source-tools-wave1/boundaries")
def boundaries() -> dict[str, Any]:
    return {"result": "PASS", **_boundaries()}
