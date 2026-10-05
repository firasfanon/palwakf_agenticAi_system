from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping


CAPABILITY_ID = "runtime.maintenance.promote_bounded_v1"
SERVICE_NAME = "PalWakfOutboundLocalExecutorV1"
TARGET_MODULE = Path(
    r"C:\Program Files\Python311\Lib\site-packages\palwakf_local_agents\workspace_drive_remote_intent_v1.py"
)
SOURCE_RELATIVE = Path(
    "backend/src/palwakf_local_agents/workspace_drive_remote_intent_v1.py"
)
DRIVE_ROOT = Path(r"C:\ProgramData\PalWakf\outbound_executor_v1\drive")
SECRET_TEMP_ROOT = DRIVE_ROOT / "rclone-secret-temp"
RESIDUE_PREFIX = "palwakf-rclone-config-"
PLAN_SCHEMA = "palwakf.runtime.maintenance.plan.v1"
RECEIPT_SCHEMA = "palwakf.runtime.maintenance.receipt.v1"
HEX64 = frozenset("0123456789abcdef")


class RuntimeMaintenanceError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeMaintenanceError("MAINTENANCE_FILE_NOT_FOUND")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_sha(value: Any, code: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(ch not in HEX64 for ch in text):
        raise RuntimeMaintenanceError(code)
    return text


def _canonical_under(path: Path, root: Path) -> bool:
    target = path.resolve()
    base = root.resolve()
    return target == base or base in target.parents


def _canonical_under_any(path: Path, roots: tuple[str, ...]) -> bool:
    target = path.resolve()
    for raw in roots:
        root = Path(raw).expanduser().resolve()
        if target == root or root in target.parents:
            return True
    return False


def _scope_covers(path: Path, repo_root: Path, scopes: tuple[str, ...]) -> bool:
    target = path.resolve()
    for raw in scopes:
        scope = Path(raw)
        resolved = scope.expanduser().resolve() if scope.is_absolute() else (repo_root / scope).resolve()
        if target == resolved or resolved in target.parents:
            return True
    return False


def _run_fixed(argv: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeMaintenanceError("MAINTENANCE_FIXED_COMMAND_FAILED") from exc


def _service_state() -> str:
    result = _run_fixed(["sc.exe", "query", SERVICE_NAME], timeout=30)
    if result.returncode != 0:
        raise RuntimeMaintenanceError("MAINTENANCE_SERVICE_QUERY_FAILED")
    text = result.stdout.decode("utf-8", errors="replace")
    if "RUNNING" in text:
        return "RUNNING"
    if "STOPPED" in text:
        return "STOPPED"
    return "TRANSITIONAL"


def _wait_service(expected: str, *, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _service_state() == expected:
            return
        time.sleep(0.5)
    raise RuntimeMaintenanceError(f"MAINTENANCE_SERVICE_{expected}_TIMEOUT")


def _set_secret_temp_acl() -> str:
    SECRET_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    commands = [
        ["icacls.exe", str(SECRET_TEMP_ROOT), "/inheritance:r"],
        [
            "icacls.exe",
            str(SECRET_TEMP_ROOT),
            "/grant:r",
            "*S-1-5-18:(OI)(CI)F",
            "*S-1-5-32-544:(OI)(CI)F",
        ],
    ]
    for argv in commands:
        result = _run_fixed(argv, timeout=30)
        if result.returncode != 0:
            raise RuntimeMaintenanceError("MAINTENANCE_ACL_ENFORCEMENT_FAILED")
    readback = _run_fixed(["icacls.exe", str(SECRET_TEMP_ROOT)], timeout=30)
    if readback.returncode != 0:
        raise RuntimeMaintenanceError("MAINTENANCE_ACL_READBACK_FAILED")
    text = readback.stdout.decode("utf-8", errors="replace")
    if "BUILTIN\\Users:(R)" in text or "BUILTIN\\Users:(RX)" in text:
        raise RuntimeMaintenanceError("MAINTENANCE_ACL_BROAD_USERS_REMAIN")
    return hashlib.sha256(readback.stdout).hexdigest()


def _classify_residue() -> list[Path]:
    stale: list[Path] = []
    if not DRIVE_ROOT.is_dir():
        raise RuntimeMaintenanceError("MAINTENANCE_DRIVE_ROOT_MISSING")
    for candidate in DRIVE_ROOT.glob(f"{RESIDUE_PREFIX}*"):
        if candidate.is_symlink() or not candidate.is_dir():
            raise RuntimeMaintenanceError("MAINTENANCE_RESIDUE_UNKNOWN_FAIL_CLOSED")
        config = candidate / "rclone.conf"
        other = [item for item in candidate.iterdir() if item.name != "rclone.conf"]
        if other or not config.is_file() or config.is_symlink():
            raise RuntimeMaintenanceError("MAINTENANCE_RESIDUE_UNKNOWN_FAIL_CLOSED")
        stale.append(candidate)
    return stale


def _cleanup_stale_residue() -> int:
    stale = _classify_residue()
    for path in stale:
        shutil.rmtree(path)
    remaining = _classify_residue()
    if remaining:
        raise RuntimeMaintenanceError("MAINTENANCE_RESIDUE_CLEANUP_INCOMPLETE")
    return len(stale)


@dataclass(frozen=True)
class MaintenancePlan:
    plan_id: str
    source_path: str
    target_path: str
    expected_source_sha256: str
    expected_runtime_sha256: str
    backup_path: str
    receipt_path: str
    issued_at: str
    expires_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": PLAN_SCHEMA,
            "plan_id": self.plan_id,
            "service_name": SERVICE_NAME,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "expected_source_sha256": self.expected_source_sha256,
            "expected_runtime_sha256": self.expected_runtime_sha256,
            "backup_path": self.backup_path,
            "receipt_path": self.receipt_path,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


def prepare_plan(
    *,
    repo_root: str,
    state_dir: str,
    expected_source_sha256: Any,
    expected_runtime_sha256: Any,
    expected_head: str,
    allowed_roots: tuple[str, ...],
    scope_paths: tuple[str, ...],
) -> Mapping[str, Any]:
    root = Path(repo_root).resolve()
    if not _canonical_under_any(root, allowed_roots):
        raise RuntimeMaintenanceError("MAINTENANCE_REPO_OUTSIDE_ALLOWED_ROOTS")
    if not (root / ".git").exists():
        raise RuntimeMaintenanceError("MAINTENANCE_REPO_INVALID")
    source = (root / SOURCE_RELATIVE).resolve()
    if not _canonical_under(source, root):
        raise RuntimeMaintenanceError("MAINTENANCE_SOURCE_OUTSIDE_REPO")
    if not _scope_covers(source, root, scope_paths):
        raise RuntimeMaintenanceError("MAINTENANCE_SOURCE_SCOPE_DENIED")
    source_sha = _validate_sha(expected_source_sha256, "MAINTENANCE_SOURCE_SHA_INVALID")
    runtime_sha = _validate_sha(expected_runtime_sha256, "MAINTENANCE_RUNTIME_SHA_INVALID")

    head = _run_fixed(
        [
            "git",
            "-c",
            f"safe.directory={root}",
            "-C",
            str(root),
            "rev-parse",
            "HEAD",
        ],
        timeout=30,
    )
    if head.returncode != 0:
        raise RuntimeMaintenanceError("MAINTENANCE_GIT_HEAD_READ_FAILED")
    observed_head = head.stdout.decode("ascii", errors="replace").strip().lower()
    if observed_head != str(expected_head).lower():
        raise RuntimeMaintenanceError("MAINTENANCE_HEAD_DRIFT")
    if _sha256(source) != source_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_SOURCE_HASH_MISMATCH")
    if _sha256(TARGET_MODULE) != runtime_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_RUNTIME_HASH_MISMATCH")
    if _service_state() != "RUNNING":
        raise RuntimeMaintenanceError("MAINTENANCE_SERVICE_NOT_RUNNING")

    state = Path(state_dir).resolve()
    state.mkdir(parents=True, exist_ok=True)
    plans = state / "runtime-maintenance"
    plans.mkdir(parents=True, exist_ok=True)
    plan_id = hashlib.sha256(
        f"{observed_head}:{source_sha}:{runtime_sha}".encode("ascii")
    ).hexdigest()[:24]
    backup = plans / f"{plan_id}.pre.py"
    receipt = plans / f"{plan_id}.receipt.json"
    plan_path = plans / f"{plan_id}.plan.json"
    shutil.copy2(TARGET_MODULE, backup)
    if _sha256(backup) != runtime_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_BACKUP_HASH_MISMATCH")

    now = datetime.now(UTC)
    plan = MaintenancePlan(
        plan_id=plan_id,
        source_path=str(source),
        target_path=str(TARGET_MODULE),
        expected_source_sha256=source_sha,
        expected_runtime_sha256=runtime_sha,
        backup_path=str(backup),
        receipt_path=str(receipt),
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    temp = plan_path.with_suffix(".tmp")
    temp.write_text(json.dumps(plan.as_dict(), sort_keys=True, indent=2), encoding="utf-8")
    os.replace(temp, plan_path)
    return {
        "plan_id": plan_id,
        "plan_path": str(plan_path),
        "receipt_path": str(receipt),
        "source_sha256": source_sha,
        "runtime_pre_sha256": runtime_sha,
        "backup_sha256": _sha256(backup),
        "service_state": "RUNNING",
    }


def execute_plan_file(plan_path: str) -> Mapping[str, Any]:
    path = Path(plan_path).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_id") != PLAN_SCHEMA or raw.get("service_name") != SERVICE_NAME:
        raise RuntimeMaintenanceError("MAINTENANCE_PLAN_INVALID")
    expires = datetime.fromisoformat(str(raw["expires_at"]))
    if datetime.now(UTC) > expires:
        raise RuntimeMaintenanceError("MAINTENANCE_PLAN_EXPIRED")

    source = Path(str(raw["source_path"])).resolve()
    target = Path(str(raw["target_path"])).resolve()
    backup = Path(str(raw["backup_path"])).resolve()
    receipt = Path(str(raw["receipt_path"])).resolve()
    if target != TARGET_MODULE.resolve():
        raise RuntimeMaintenanceError("MAINTENANCE_TARGET_NOT_ALLOWLISTED")
    if not _canonical_under(source, Path.cwd()):
        # The helper is launched with cwd=repo_root.
        raise RuntimeMaintenanceError("MAINTENANCE_SOURCE_NOT_ALLOWLISTED")

    source_sha = _validate_sha(raw.get("expected_source_sha256"), "MAINTENANCE_SOURCE_SHA_INVALID")
    runtime_sha = _validate_sha(raw.get("expected_runtime_sha256"), "MAINTENANCE_RUNTIME_SHA_INVALID")
    if _sha256(source) != source_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_SOURCE_HASH_MISMATCH")
    if _sha256(target) != runtime_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_RUNTIME_HASH_MISMATCH")
    if _sha256(backup) != runtime_sha:
        raise RuntimeMaintenanceError("MAINTENANCE_BACKUP_HASH_MISMATCH")

    cleaned = 0
    try:
        shutil.copy2(source, target)
        if _sha256(target) != source_sha:
            raise RuntimeMaintenanceError("MAINTENANCE_RUNTIME_POST_HASH_MISMATCH")
        _set_secret_temp_acl()
        cleaned = _cleanup_stale_residue()
        stop = _run_fixed(["sc.exe", "stop", SERVICE_NAME], timeout=30)
        if stop.returncode not in {0, 1062}:
            raise RuntimeMaintenanceError("MAINTENANCE_SERVICE_STOP_FAILED")
        _wait_service("STOPPED", timeout_seconds=30)
        start = _run_fixed(["sc.exe", "start", SERVICE_NAME], timeout=30)
        if start.returncode not in {0, 1056}:
            raise RuntimeMaintenanceError("MAINTENANCE_SERVICE_START_FAILED")
        _wait_service("RUNNING", timeout_seconds=30)
        result = {
            "schema_id": RECEIPT_SCHEMA,
            "plan_id": str(raw["plan_id"]),
            "status": "PASS",
            "runtime_post_sha256": _sha256(target),
            "stale_residue_removed": cleaned,
            "stale_residue_remaining": len(_classify_residue()),
            "service_state": _service_state(),
            "secret_temp_acl_readback_sha256": _set_secret_temp_acl(),
            "secret_values_read": False,
        }
    except Exception as exc:
        rollback = "NOT_NEEDED"
        try:
            if target.is_file() and _sha256(target) != runtime_sha:
                shutil.copy2(backup, target)
                rollback = "PASS" if _sha256(target) == runtime_sha else "FAIL"
        except Exception:
            rollback = "FAIL"
        result = {
            "schema_id": RECEIPT_SCHEMA,
            "plan_id": str(raw.get("plan_id") or ""),
            "status": "FAIL",
            "error": type(exc).__name__,
            "rollback": rollback,
            "secret_values_read": False,
        }
    temp = receipt.with_suffix(".tmp")
    temp.write_text(json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
    os.replace(temp, receipt)
    return result


def launch_helper(*, repo_root: str, plan_path: str) -> Mapping[str, Any]:
    root = Path(repo_root).resolve()
    plan = Path(plan_path).resolve()
    if not _canonical_under(plan, Path(r"C:\ProgramData\PalWakf\outbound_executor_v1\state")):
        raise RuntimeMaintenanceError("MAINTENANCE_PLAN_PATH_NOT_ALLOWLISTED")
    flags = 0
    if os.name == "nt":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "palwakf_local_agents.governed_runtime_maintenance_v1",
            "--execute-plan",
            str(plan),
        ],
        cwd=str(root),
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return {"helper_pid": process.pid, "plan_path": str(plan), "state": "HANDOFF_LAUNCHED"}


def read_receipt(*, receipt_path: str) -> Mapping[str, Any]:
    receipt = Path(receipt_path).resolve()
    if not _canonical_under(receipt, Path(r"C:\ProgramData\PalWakf\outbound_executor_v1\state")):
        raise RuntimeMaintenanceError("MAINTENANCE_RECEIPT_PATH_NOT_ALLOWLISTED")
    if not receipt.is_file():
        return {"state": "PENDING"}
    raw = json.loads(receipt.read_text(encoding="utf-8"))
    if raw.get("schema_id") != RECEIPT_SCHEMA:
        raise RuntimeMaintenanceError("MAINTENANCE_RECEIPT_INVALID")
    return dict(raw)


def runtime_maintenance_capability(ctx: Any, args: Mapping[str, Any]) -> Mapping[str, Any]:
    allowed = {
        "operation",
        "repo_root",
        "expected_source_sha256",
        "expected_runtime_sha256",
        "plan_path",
        "receipt_path",
    }
    if set(args) - allowed:
        raise RuntimeMaintenanceError("MAINTENANCE_ARGUMENT_NOT_ALLOWED")
    operation = str(args.get("operation") or "")
    repo_root = str(args.get("repo_root") or "")
    if operation == "prepare":
        return prepare_plan(
            repo_root=repo_root,
            state_dir=str(ctx.state_dir or ""),
            expected_source_sha256=args.get("expected_source_sha256"),
            expected_runtime_sha256=args.get("expected_runtime_sha256"),
            expected_head=str(ctx.expected_base_sha),
            allowed_roots=tuple(ctx.allowed_roots),
            scope_paths=tuple(ctx.scope_paths),
        )
    if operation == "launch":
        return launch_helper(repo_root=repo_root, plan_path=str(args.get("plan_path") or ""))
    if operation == "status":
        return read_receipt(receipt_path=str(args.get("receipt_path") or ""))
    raise RuntimeMaintenanceError("MAINTENANCE_OPERATION_NOT_ALLOWED")


def _main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--execute-plan":
        result = execute_plan_file(argv[1])
        return 0 if result.get("status") == "PASS" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
