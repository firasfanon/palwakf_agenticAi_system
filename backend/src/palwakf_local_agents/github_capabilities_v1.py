from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Protocol


class GitHubCapabilityError(RuntimeError):
    pass


class GitHubCapabilityContext(Protocol):
    repository_id: str
    allowed_roots: tuple[str, ...]
    scope_paths: tuple[str, ...]
    task_branch: str
    expected_base_sha: str
    max_output_bytes: int


def _run(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    max_bytes: int = 131072,
) -> dict[str, Any]:
    if not argv or any(not isinstance(item, str) or "\x00" in item for item in argv):
        raise GitHubCapabilityError("INVALID_ARGV")
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
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


def _rooted_repo(path: str, allowed_roots: tuple[str, ...]) -> Path:
    target = Path(path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not roots:
        raise GitHubCapabilityError("NO_ALLOWED_ROOTS")
    if not any(target == root or root in target.parents for root in roots):
        raise GitHubCapabilityError("REPO_OUTSIDE_ALLOWED_ROOTS")
    git_probe = _run(["git", "rev-parse", "--show-toplevel"], cwd=target)
    if git_probe["exit_code"] != 0:
        raise GitHubCapabilityError("NOT_A_GIT_WORKTREE")
    top = Path(git_probe["stdout"].strip()).resolve()
    if top != target:
        raise GitHubCapabilityError("REPO_ROOT_MUST_BE_WORKTREE_TOPLEVEL")
    return target


def _canonical_repo_from_origin(origin: str) -> str | None:
    value = origin.strip().replace("\\", "/")
    patterns = (
        r"^https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
        r"^git@github\.com:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group("repo")
    return None


def _require_repo_binding(ctx: GitHubCapabilityContext, repo: Path) -> str:
    remote = _run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if remote["exit_code"] != 0:
        raise GitHubCapabilityError("ORIGIN_READ_FAILED")
    observed = _canonical_repo_from_origin(remote["stdout"])
    if observed is None or observed.casefold() != ctx.repository_id.casefold():
        raise GitHubCapabilityError("SIGNED_REPOSITORY_ORIGIN_MISMATCH")
    return observed


def _current_branch(ctx: GitHubCapabilityContext, repo: Path) -> str:
    result = _run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if result["exit_code"] != 0:
        raise GitHubCapabilityError("CURRENT_BRANCH_READ_FAILED")
    return result["stdout"].strip()


def _scope_roots(ctx: GitHubCapabilityContext, repo: Path) -> tuple[Path, ...]:
    roots: list[Path] = []
    for item in ctx.scope_paths:
        raw = Path(item).expanduser()
        target = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
        if target != repo and repo not in target.parents:
            raise GitHubCapabilityError("SIGNED_SCOPE_OUTSIDE_REPOSITORY")
        roots.append(target)
    return tuple(roots)


def _bounded_path(
    ctx: GitHubCapabilityContext,
    repo: Path,
    relative_path: str,
    *,
    require_write_scope: bool,
) -> Path:
    raw = Path(relative_path)
    if raw.is_absolute() or not relative_path or ".." in raw.parts:
        raise GitHubCapabilityError("UNSAFE_REPOSITORY_PATH")
    target = (repo / raw).resolve()
    if target != repo and repo not in target.parents:
        raise GitHubCapabilityError("PATH_OUTSIDE_REPOSITORY")
    if require_write_scope:
        scopes = _scope_roots(ctx, repo)
        if not scopes:
            raise GitHubCapabilityError("WRITE_SCOPE_REQUIRED")
        if not any(target == scope or scope in target.parents for scope in scopes):
            raise GitHubCapabilityError("PATH_OUTSIDE_SIGNED_SCOPE")
    return target


def _sha256_or_none(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def github_repo_read(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    observed = _require_repo_binding(ctx, repo)
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo, max_bytes=ctx.max_output_bytes)
    branch = _current_branch(ctx, repo)
    status = _run(
        ["git", "status", "--porcelain=v1"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if head["exit_code"] != 0 or status["exit_code"] != 0:
        raise GitHubCapabilityError("REPOSITORY_READ_FAILED")
    return {
        "repository_id": observed,
        "head": head["stdout"].strip(),
        "branch": branch,
        "worktree_clean": not bool(status["stdout"].strip()),
    }


def github_branch_read(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    branch = str(args.get("branch") or ctx.task_branch)
    if not branch or branch.startswith("-"):
        raise GitHubCapabilityError("BRANCH_INVALID")
    local = _run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    remote = _run(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if remote["exit_code"] != 0:
        raise GitHubCapabilityError("REMOTE_BRANCH_READ_FAILED")
    remote_line = remote["stdout"].strip()
    remote_sha = remote_line.split()[0] if remote_line else None
    return {
        "branch": branch,
        "local_sha": local["stdout"].strip() if local["exit_code"] == 0 else None,
        "remote_sha": remote_sha,
    }


def github_diff_read(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    base = str(args.get("base") or ctx.expected_base_sha)
    head = str(args.get("head") or "HEAD")
    paths = args.get("paths") or []
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        raise GitHubCapabilityError("DIFF_PATHS_INVALID")
    clean_paths: list[str] = []
    for item in paths:
        _bounded_path(ctx, repo, item, require_write_scope=False)
        clean_paths.append(item)
    argv = ["git", "diff", "--no-ext-diff", "--binary", base, head]
    if clean_paths:
        argv.extend(["--", *clean_paths])
    result = _run(argv, cwd=repo, max_bytes=ctx.max_output_bytes)
    if result["exit_code"] != 0:
        raise GitHubCapabilityError("GIT_DIFF_READ_FAILED")
    return {
        "base": base,
        "head": head,
        "paths": clean_paths,
        "diff": result["stdout"],
        "truncated": result["stdout_truncated"],
    }


def github_file_read(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    relative = str(args.get("path", ""))
    target = _bounded_path(ctx, repo, relative, require_write_scope=False)
    if not target.is_file():
        raise GitHubCapabilityError("FILE_NOT_FOUND")
    max_bytes = int(args.get("max_bytes", min(65536, ctx.max_output_bytes)))
    if max_bytes < 1 or max_bytes > ctx.max_output_bytes:
        raise GitHubCapabilityError("FILE_READ_MAX_BYTES_INVALID")
    data = target.read_bytes()
    return {
        "path": relative,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content": data[:max_bytes].decode("utf-8", errors="replace"),
        "truncated": len(data) > max_bytes,
    }


def github_file_write_bounded(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    if _current_branch(ctx, repo) != ctx.task_branch:
        raise GitHubCapabilityError("CURRENT_BRANCH_MISMATCH")
    relative = str(args.get("path", ""))
    target = _bounded_path(ctx, repo, relative, require_write_scope=True)
    content = args.get("content")
    if not isinstance(content, str):
        raise GitHubCapabilityError("TEXT_CONTENT_REQUIRED")
    encoded = content.encode("utf-8")
    if len(encoded) > 262144:
        raise GitHubCapabilityError("FILE_WRITE_TOO_LARGE")
    before = _sha256_or_none(target)
    expected = args.get("expected_sha256")
    if before is None:
        if expected not in {None, ""}:
            raise GitHubCapabilityError("EXPECTED_SHA_FOR_NEW_FILE_MUST_BE_EMPTY")
    else:
        if not isinstance(expected, str) or expected.lower() != before:
            raise GitHubCapabilityError("FILE_CONTENT_DRIFT")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".palwakf.tmp")
    tmp.write_bytes(encoded)
    tmp.replace(target)
    after = hashlib.sha256(encoded).hexdigest()
    return {
        "path": relative,
        "before_sha256": before,
        "after_sha256": after,
        "bytes": len(encoded),
    }


def github_branch_create(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    branch = str(args.get("branch", ""))
    base_sha = str(args.get("base_sha", ""))
    if branch != ctx.task_branch or not branch.startswith("task/"):
        raise GitHubCapabilityError("TASK_BRANCH_MISMATCH")
    if base_sha.lower() != ctx.expected_base_sha.lower():
        raise GitHubCapabilityError("BASE_SHA_MISMATCH")
    status = _run(
        ["git", "status", "--porcelain=v1"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if status["exit_code"] != 0 or status["stdout"].strip():
        raise GitHubCapabilityError("WORKTREE_NOT_CLEAN")
    result = _run(
        ["git", "switch", "-c", branch, base_sha],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if result["exit_code"] != 0:
        raise GitHubCapabilityError("TASK_BRANCH_CREATE_FAILED")
    return {"branch": branch, "base_sha": base_sha}


def github_commit_create(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    if _current_branch(ctx, repo) != ctx.task_branch:
        raise GitHubCapabilityError("CURRENT_BRANCH_MISMATCH")
    paths = args.get("paths")
    if not isinstance(paths, list) or not paths:
        raise GitHubCapabilityError("COMMIT_PATHS_REQUIRED")
    clean: list[str] = []
    for item in paths:
        if not isinstance(item, str) or item in {".", "*"}:
            raise GitHubCapabilityError("UNSAFE_COMMIT_PATH")
        _bounded_path(ctx, repo, item, require_write_scope=True)
        clean.append(item)
    message = str(args.get("message", "")).strip()
    if not message or len(message) > 240:
        raise GitHubCapabilityError("COMMIT_MESSAGE_INVALID")
    stage = _run(
        ["git", "add", "--", *clean],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if stage["exit_code"] != 0:
        raise GitHubCapabilityError("GIT_STAGE_FAILED")
    staged = _run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    staged_paths = [item for item in staged["stdout"].splitlines() if item.strip()]
    if sorted(staged_paths) != sorted(clean):
        raise GitHubCapabilityError("STAGED_PATH_SET_MISMATCH")
    result = _run(
        ["git", "commit", "-m", message],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if result["exit_code"] != 0:
        raise GitHubCapabilityError("GIT_COMMIT_FAILED")
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo)["stdout"].strip()
    return {"commit_sha": head, "paths": clean}


def github_task_branch_push(
    ctx: GitHubCapabilityContext,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
    _require_repo_binding(ctx, repo)
    branch = str(args.get("branch", ""))
    if branch != ctx.task_branch or not branch.startswith("task/"):
        raise GitHubCapabilityError("PUSH_TASK_BRANCH_MISMATCH")
    if _current_branch(ctx, repo) != branch:
        raise GitHubCapabilityError("CURRENT_BRANCH_MISMATCH")
    expected_remote = str(args.get("expected_remote_head", ""))
    if expected_remote.lower() != ctx.expected_base_sha.lower():
        raise GitHubCapabilityError("SIGNED_REMOTE_PRECONDITION_MISMATCH")
    remote = _run(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    if remote["exit_code"] != 0:
        raise GitHubCapabilityError("REMOTE_HEAD_READ_FAILED")
    line = remote["stdout"].strip()
    observed = line.split()[0] if line else None
    if observed is not None and observed.lower() != expected_remote.lower():
        raise GitHubCapabilityError("REMOTE_HEAD_DRIFT")
    push = _run(
        ["git", "push", "origin", f"HEAD:refs/heads/{branch}"],
        cwd=repo,
        timeout=180,
        max_bytes=ctx.max_output_bytes,
    )
    if push["exit_code"] != 0:
        raise GitHubCapabilityError("TASK_BRANCH_PUSH_FAILED")
    head = _run(["git", "rev-parse", "HEAD"], cwd=repo)["stdout"].strip()
    verify = _run(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        cwd=repo,
        max_bytes=ctx.max_output_bytes,
    )
    verify_line = verify["stdout"].strip()
    remote_after = verify_line.split()[0] if verify_line else None
    if remote_after != head:
        raise GitHubCapabilityError("REMOTE_PUSH_READBACK_MISMATCH")
    return {
        "branch": branch,
        "before_remote_sha": observed,
        "after_remote_sha": remote_after,
        "force": False,
    }


def extra_github_capabilities_v1():
    from palwakf_local_agents.outbound_capabilities_v1 import (
        CapabilityDescriptorV1,
        CapabilityError,
    )

    def adapt(handler):
        def wrapped(ctx, args):
            try:
                return handler(ctx, args)
            except GitHubCapabilityError as exc:
                raise CapabilityError(str(exc)) from exc

        return wrapped

    return (
        CapabilityDescriptorV1(
            "github.repo.read",
            "READ_ONLY",
            adapt(github_repo_read),
        ),
        CapabilityDescriptorV1(
            "github.branch.read",
            "READ_ONLY",
            adapt(github_branch_read),
        ),
        CapabilityDescriptorV1(
            "github.diff.read",
            "READ_ONLY",
            adapt(github_diff_read),
        ),
        CapabilityDescriptorV1(
            "github.file.read",
            "READ_ONLY",
            adapt(github_file_read),
        ),
        CapabilityDescriptorV1(
            "github.branch.create",
            "SOURCE_WRITE",
            adapt(github_branch_create),
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "github.file.write_bounded",
            "SOURCE_WRITE",
            adapt(github_file_write_bounded),
            idempotency_class="STATEFUL_GOVERNED",
        ),
        CapabilityDescriptorV1(
            "github.commit.create",
            "SOURCE_WRITE",
            adapt(github_commit_create),
            idempotency_class="NON_IDEMPOTENT",
        ),
        CapabilityDescriptorV1(
            "github.task_branch.push",
            "SOURCE_WRITE",
            adapt(github_task_branch_push),
            idempotency_class="NON_IDEMPOTENT",
        ),
    )