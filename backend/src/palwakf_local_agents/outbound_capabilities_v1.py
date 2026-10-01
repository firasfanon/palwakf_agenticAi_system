from __future__ import annotations

import hashlib
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping

from palwakf_local_agents.c7r_phase_a_v1 import C7RPhaseAError, c7r_phase_a


MutationClass = Literal["READ_ONLY", "TEMP_MUTATION", "SOURCE_WRITE", "SERVICE_MUTATION"]

LEGACY_TEN_CAPABILITY_NAMES: tuple[str, ...] = (
    "mesh_device_info",
    "mesh_hostname",
    "file_read",
    "temp_write",
    "temp_delete",
    "bounded_powershell",
    "process_port_readback",
    "git_readback",
    "playwright_screenshot_uat",
    "audit_readback",
)


class CapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapabilityContextV1:
    executor_id: str
    repository_id: str
    allowed_roots: tuple[str, ...]
    scope_paths: tuple[str, ...]
    task_branch: str
    expected_base_sha: str
    max_output_bytes: int = 131072


@dataclass(frozen=True)
class CapabilityDescriptorV1:
    capability_id: str
    mutation_class: MutationClass
    handler: Callable[[CapabilityContextV1, Mapping[str, Any]], Mapping[str, Any]]
    aliases: tuple[str, ...] = ()
    admitted: bool = True
    idempotency_class: str = "IDEMPOTENT"


class CapabilityRegistryV1:
    def __init__(self, descriptors: tuple[CapabilityDescriptorV1, ...]):
        by_id: dict[str, CapabilityDescriptorV1] = {}
        aliases: dict[str, str] = {}
        for item in descriptors:
            if item.capability_id in by_id:
                raise ValueError("DUPLICATE_CAPABILITY_ID")
            by_id[item.capability_id] = item
            for alias in item.aliases:
                if alias in aliases:
                    raise ValueError("DUPLICATE_CAPABILITY_ALIAS")
                aliases[alias] = item.capability_id
        self._by_id = by_id
        self._aliases = aliases

    def resolve(self, capability_id: str) -> CapabilityDescriptorV1:
        canonical = self._aliases.get(capability_id, capability_id)
        item = self._by_id.get(canonical)
        if item is None or not item.admitted:
            raise CapabilityError("CAPABILITY_UNKNOWN_OR_NOT_ADMITTED")
        return item

    def descriptors(self) -> tuple[CapabilityDescriptorV1, ...]:
        return tuple(self._by_id.values())


def _run(argv: list[str], *, cwd: str, timeout: int = 120, max_bytes: int = 131072) -> dict[str, Any]:
    if not argv or any(not isinstance(x, str) or "\x00" in x for x in argv):
        raise CapabilityError("INVALID_ARGV")
    completed = subprocess.run(
        argv,
        cwd=cwd,
        shell=False,
        capture_output=True,
        text=False,
        timeout=timeout,
        check=False,
    )
    stdout = completed.stdout[:max_bytes]
    stderr = completed.stderr[:max_bytes]
    return {
        "exit_code": completed.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "stdout_truncated": len(completed.stdout) > max_bytes,
        "stderr_truncated": len(completed.stderr) > max_bytes,
    }


def _rooted(path: str, allowed_roots: tuple[str, ...]) -> Path:
    target = Path(path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not roots:
        raise CapabilityError("NO_ALLOWED_ROOTS")
    if not any(target == root or root in target.parents for root in roots):
        raise CapabilityError("PATH_OUTSIDE_ALLOWED_ROOTS")
    return target


def c7r_phase_a_handler(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    try:
        return c7r_phase_a(ctx, args)
    except C7RPhaseAError as exc:
        raise CapabilityError(str(exc)) from exc


def device_hostname(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if args:
        raise CapabilityError("HOSTNAME_TAKES_NO_ARGUMENTS")
    return {"hostname": platform.node(), "executor_id": ctx.executor_id}


def device_info(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if args:
        raise CapabilityError("DEVICE_INFO_TAKES_NO_ARGUMENTS")
    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "executor_id": ctx.executor_id,
    }


def file_read(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    path = str(args.get("path", ""))
    max_bytes = int(args.get("max_bytes", min(65536, ctx.max_output_bytes)))
    if max_bytes < 1 or max_bytes > ctx.max_output_bytes:
        raise CapabilityError("FILE_READ_MAX_BYTES_INVALID")
    target = _rooted(path, ctx.allowed_roots)
    if not target.is_file():
        raise CapabilityError("FILE_NOT_FOUND")
    data = target.read_bytes()
    chunk = data[:max_bytes]
    return {
        "path": str(target),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content": chunk.decode("utf-8", errors="replace"),
        "truncated": len(data) > max_bytes,
    }


def git_readback(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    if not (repo / ".git").exists():
        raise CapabilityError("NOT_A_GIT_WORKTREE")
    head = _run(["git", "rev-parse", "HEAD"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    branch = _run(["git", "branch", "--show-current"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    status = _run(["git", "status", "--porcelain=v1"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    remote = _run(["git", "remote", "get-url", "origin"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    return {
        "head": head["stdout"].strip(),
        "branch": branch["stdout"].strip(),
        "status_porcelain": status["stdout"],
        "origin": remote["stdout"].strip(),
        "exit_codes": {"head": head["exit_code"], "branch": branch["exit_code"], "status": status["exit_code"], "remote": remote["exit_code"]},
    }


def git_create_task_branch(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    branch = str(args.get("branch", ""))
    base_sha = str(args.get("base_sha", ""))
    if branch != ctx.task_branch or not branch.startswith("task/"):
        raise CapabilityError("TASK_BRANCH_MISMATCH")
    if base_sha.lower() != ctx.expected_base_sha.lower():
        raise CapabilityError("BASE_SHA_MISMATCH")
    status = _run(["git", "status", "--porcelain=v1"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if status["exit_code"] != 0 or status["stdout"].strip():
        raise CapabilityError("WORKTREE_NOT_CLEAN")
    verify = _run(["git", "cat-file", "-e", f"{base_sha}^{{commit}}"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if verify["exit_code"] != 0:
        raise CapabilityError("BASE_COMMIT_NOT_PRESENT")
    exists = _run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if exists["exit_code"] == 0:
        raise CapabilityError("TASK_BRANCH_ALREADY_EXISTS")
    result = _run(["git", "switch", "-c", branch, base_sha], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise CapabilityError("TASK_BRANCH_CREATE_FAILED")
    return {"branch": branch, "base_sha": base_sha, "result": result}


def git_stage_paths(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    paths = args.get("paths")
    if not isinstance(paths, list) or not paths:
        raise CapabilityError("STAGE_PATHS_REQUIRED")
    clean: list[str] = []
    for item in paths:
        if not isinstance(item, str) or item in {".", "*"} or ".." in Path(item).parts:
            raise CapabilityError("UNSAFE_STAGE_PATH")
        clean.append(item)
    result = _run(["git", "add", "--", *clean], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise CapabilityError("GIT_STAGE_FAILED")
    return {"staged_paths": clean, "result": result}


def git_commit(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    message = str(args.get("message", "")).strip()
    if not message or len(message) > 240:
        raise CapabilityError("COMMIT_MESSAGE_INVALID")
    branch = _run(["git", "branch", "--show-current"], cwd=str(repo), max_bytes=ctx.max_output_bytes)["stdout"].strip()
    if branch != ctx.task_branch:
        raise CapabilityError("CURRENT_BRANCH_MISMATCH")
    result = _run(["git", "commit", "-m", message], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise CapabilityError("GIT_COMMIT_FAILED")
    head = _run(["git", "rev-parse", "HEAD"], cwd=str(repo), max_bytes=ctx.max_output_bytes)["stdout"].strip()
    return {"commit_sha": head, "result": result}


def git_push_task_branch(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    branch = str(args.get("branch", ""))
    if branch != ctx.task_branch or not branch.startswith("task/"):
        raise CapabilityError("PUSH_TASK_BRANCH_MISMATCH")
    current = _run(["git", "branch", "--show-current"], cwd=str(repo), max_bytes=ctx.max_output_bytes)["stdout"].strip()
    if current != branch:
        raise CapabilityError("CURRENT_BRANCH_MISMATCH")
    result = _run(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise CapabilityError("GIT_PUSH_FAILED")
    return {"branch": branch, "force": False, "result": result}


def git_remote_sha_readback(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    branch = str(args.get("branch", ""))
    if not branch.startswith("task/"):
        raise CapabilityError("REMOTE_READBACK_TASK_BRANCH_REQUIRED")
    result = _run(["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"], cwd=str(repo), max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise CapabilityError("REMOTE_SHA_READBACK_FAILED")
    line = result["stdout"].strip()
    sha = line.split()[0] if line else None
    return {"branch": branch, "remote_sha": sha, "result": result}


def audit_readback(ctx: CapabilityContextV1, args: Mapping[str, Any]) -> Mapping[str, Any]:
    ledger = _rooted(str(args.get("ledger_path", "")), ctx.allowed_roots)
    if not ledger.is_file():
        raise CapabilityError("AUDIT_LEDGER_NOT_FOUND")
    lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = lines[-min(50, int(args.get("limit", 20))):]
    digest = hashlib.sha256(ledger.read_bytes()).hexdigest()
    return {"line_count": len(lines), "tail": tail, "sha256": digest}


def codex_patch_proposal_handler(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    from palwakf_local_agents.codex_engineering_provider_v1 import (
        codex_patch_proposal,
    )

    return codex_patch_proposal(ctx, args)


def workspace_drive_read_handler(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    from palwakf_local_agents.workspace_drive_capabilities_v1 import (
        workspace_drive_read,
    )

    return workspace_drive_read(ctx, args)


def workspace_drive_write_handler(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    from palwakf_local_agents.workspace_drive_capabilities_v1 import (
        workspace_drive_write_bounded,
    )

    return workspace_drive_write_bounded(ctx, args)


def _scope_allows_relative_path(
    repo: Path,
    relative: str,
    scope_paths: tuple[str, ...],
) -> bool:
    target = (repo / relative).resolve()
    for raw in scope_paths:
        scope = Path(raw)
        if scope.is_absolute():
            resolved = scope.resolve()
        else:
            resolved = (repo / scope).resolve()
        if target == resolved or resolved in target.parents:
            return True
    return False


def source_apply_patch_bounded(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted(str(args.get("repo_root", "")), ctx.allowed_roots)
    patch = str(args.get("unified_diff", ""))
    paths = args.get("paths")
    if not patch or len(patch.encode("utf-8")) > ctx.max_output_bytes * 4:
        raise CapabilityError("PATCH_INVALID_OR_TOO_LARGE")
    if not isinstance(paths, list) or not paths:
        raise CapabilityError("PATCH_PATHS_REQUIRED")
    clean: list[str] = []
    for item in paths:
        if not isinstance(item, str) or not item or Path(item).is_absolute():
            raise CapabilityError("PATCH_PATH_INVALID")
        if ".." in Path(item).parts or item in {".", "*"}:
            raise CapabilityError("PATCH_PATH_INVALID")
        if not _scope_allows_relative_path(repo, item, ctx.scope_paths):
            raise CapabilityError("PATCH_SCOPE_WIDENING_DENIED")
        clean.append(item)
    for header in (
        line[4:]
        for line in patch.splitlines()
        if line.startswith("+++ ") or line.startswith("--- ")
    ):
        candidate = header.split("\t", 1)[0]
        if candidate == "/dev/null":
            continue
        if candidate.startswith(("a/", "b/")):
            candidate = candidate[2:]
        if candidate not in clean:
            raise CapabilityError("PATCH_HEADER_PATH_NOT_DECLARED")
    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=error-all", "-"],
        cwd=str(repo),
        input=patch.encode("utf-8"),
        shell=False,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if check.returncode != 0:
        raise CapabilityError("PATCH_CHECK_FAILED")
    apply_result = subprocess.run(
        ["git", "apply", "--whitespace=error-all", "-"],
        cwd=str(repo),
        input=patch.encode("utf-8"),
        shell=False,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if apply_result.returncode != 0:
        raise CapabilityError("PATCH_APPLY_FAILED")
    return {"applied_paths": clean, "git_refs_mutated": False}


def default_capability_registry_v1() -> CapabilityRegistryV1:
    implemented = (
        CapabilityDescriptorV1("device.info", "READ_ONLY", device_info, aliases=("mesh_device_info",)),
        CapabilityDescriptorV1("device.hostname", "READ_ONLY", device_hostname, aliases=("mesh_hostname",)),
        CapabilityDescriptorV1("file.read", "READ_ONLY", file_read, aliases=("file_read",)),
        CapabilityDescriptorV1("git.readback", "READ_ONLY", git_readback, aliases=("git_readback",)),
        CapabilityDescriptorV1("audit.readback", "READ_ONLY", audit_readback, aliases=("audit_readback",)),
        CapabilityDescriptorV1("git.create_task_branch", "SOURCE_WRITE", git_create_task_branch, idempotency_class="NON_IDEMPOTENT"),
        CapabilityDescriptorV1("git.stage_paths", "SOURCE_WRITE", git_stage_paths, idempotency_class="NON_IDEMPOTENT"),
        CapabilityDescriptorV1("git.commit", "SOURCE_WRITE", git_commit, idempotency_class="NON_IDEMPOTENT"),
        CapabilityDescriptorV1("git.push_task_branch", "SOURCE_WRITE", git_push_task_branch, idempotency_class="NON_IDEMPOTENT"),
        CapabilityDescriptorV1("git.remote_sha_readback", "READ_ONLY", git_remote_sha_readback),
        CapabilityDescriptorV1(
            "engineering.codex.patch_proposal",
            "READ_ONLY",
            codex_patch_proposal_handler,
            idempotency_class="IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "source.apply_patch_bounded",
            "SOURCE_WRITE",
            source_apply_patch_bounded,
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "workspace_drive.read",
            "READ_ONLY",
            workspace_drive_read_handler,
        ),
        CapabilityDescriptorV1(
            "workspace_drive.write_bounded",
            "SOURCE_WRITE",
            workspace_drive_write_handler,
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "workspace_drive.write_learning_candidate",
            "SOURCE_WRITE",
            workspace_drive_write_handler,
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "workspace_drive.write_memory_candidate",
            "SOURCE_WRITE",
            workspace_drive_write_handler,
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1("c7r.phase_a", "SERVICE_MUTATION", c7r_phase_a_handler, idempotency_class="STATEFUL_GOVERNED"),
    )
    placeholders = tuple(
        CapabilityDescriptorV1(f"legacy.{name}", "READ_ONLY", device_hostname, aliases=(name,), admitted=False)
        for name in ("temp_write", "temp_delete", "bounded_powershell", "process_port_readback", "playwright_screenshot_uat")
    )
    return CapabilityRegistryV1(implemented + placeholders)
