from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
)


class CodexEngineeringSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executable: str
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    home: str | None = None
    timeout_seconds: int = Field(default=600, ge=30, le=1800)
    max_prompt_chars: int = Field(default=30000, ge=1000, le=100000)
    max_patch_chars: int = Field(default=120000, ge=4096, le=500000)


Runner = Callable[..., subprocess.CompletedProcess[bytes]]


def _settings() -> CodexEngineeringSettingsV1:
    executable = os.environ.get("PALWAKF_CODEX_EXECUTABLE", "").strip()
    expected = os.environ.get("PALWAKF_CODEX_SHA256", "").strip().lower()
    home = (
        os.environ.get("PALWAKF_CODEX_HOME", "").strip()
        or os.environ.get("CODEX_HOME", "").strip()
        or None
    )
    if not executable or not expected:
        raise CapabilityError("CODEX_PROVIDER_NOT_CONFIGURED")
    return CodexEngineeringSettingsV1(
        executable=executable,
        expected_sha256=expected,
        home=home,
    )


def _verify_binary(settings: CodexEngineeringSettingsV1) -> Path:
    path = Path(settings.executable).resolve()
    if not path.is_file():
        raise CapabilityError("CODEX_EXECUTABLE_NOT_FOUND")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != settings.expected_sha256:
        raise CapabilityError("CODEX_EXECUTABLE_HASH_MISMATCH")
    return path


def _repo_from_context(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Path:
    repo = Path(str(args.get("repo_root", ""))).resolve()
    roots = [Path(root).resolve() for root in ctx.allowed_roots]
    if not any(repo == root or root in repo.parents for root in roots):
        raise CapabilityError("PATH_OUTSIDE_ALLOWED_ROOTS")
    if not (repo / ".git").exists():
        raise CapabilityError("NOT_A_GIT_WORKTREE")
    return repo


def _git_safe_env(repo: Path) -> dict[str, str]:
    env = os.environ.copy()
    try:
        count = int(env.get("GIT_CONFIG_COUNT", "0") or "0")
    except ValueError as exc:
        raise CapabilityError("GIT_CONFIG_COUNT_INVALID") from exc
    env[f"GIT_CONFIG_KEY_{count}"] = "safe.directory"
    env[f"GIT_CONFIG_VALUE_{count}"] = str(repo)
    env["GIT_CONFIG_COUNT"] = str(count + 1)
    return env


def _resolve_codex_home(
    settings: CodexEngineeringSettingsV1,
    executable: Path,
) -> Path:
    candidates: list[Path] = []
    if settings.home:
        candidates.append(Path(settings.home).expanduser().resolve())
    else:
        home_candidate = Path.home() / ".codex"
        candidates.append(home_candidate.resolve())
        for parent in executable.parents:
            if parent.parent.name.casefold() == "users":
                candidates.append((parent / ".codex").resolve())
                break

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "auth.json").is_file():
            return candidate
    raise CapabilityError("CODEX_AUTH_HOME_NOT_FOUND")


def _codex_env(
    settings: CodexEngineeringSettingsV1,
    executable: Path,
    repo: Path,
) -> dict[str, str]:
    env = _git_safe_env(repo)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    env["CODEX_HOME"] = str(_resolve_codex_home(settings, executable))
    return env


def _git_read(
    repo: Path,
    *args: str,
) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=_git_safe_env(repo),
    )
    if completed.returncode != 0:
        raise CapabilityError("CODEX_PROVIDER_GIT_READBACK_FAILED")
    return completed.stdout.strip()


def codex_patch_proposal(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
    *,
    runner: Runner = subprocess.run,
) -> Mapping[str, Any]:
    settings = _settings()
    executable = _verify_binary(settings)
    repo = _repo_from_context(ctx, args)
    prompt = str(args.get("prompt", "")).strip()
    if not prompt or len(prompt) > settings.max_prompt_chars:
        raise CapabilityError("CODEX_PROMPT_INVALID")

    head = _git_read(repo, "rev-parse", "HEAD")
    branch = _git_read(repo, "branch", "--show-current")
    status = _git_read(repo, "status", "--porcelain=v1")
    if head.lower() != ctx.expected_base_sha.lower():
        raise CapabilityError("CODEX_PROVIDER_HEAD_DRIFT")
    if branch != ctx.task_branch:
        raise CapabilityError("CODEX_PROVIDER_BRANCH_MISMATCH")
    if status:
        raise CapabilityError("CODEX_PROVIDER_REQUIRES_CLEAN_WORKTREE")

    policy = (
        "You are a read-only software engineering provider. "
        "Never modify files and never execute git mutations. "
        "Return JSON only with keys summary, changed_files, unified_diff, tests. "
        "The unified_diff is a proposal only. It must touch only explicitly scoped paths."
    )
    effective = policy + "\n\nAUTHORIZED REQUEST:\n" + prompt

    completed = runner(
        [
            str(executable),
            "exec",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--color",
            "never",
            "-C",
            str(repo),
            "-",
        ],
        input=effective.encode("utf-8"),
        cwd=str(repo),
        shell=False,
        capture_output=True,
        text=False,
        timeout=settings.timeout_seconds,
        check=False,
        env=_codex_env(settings, executable, repo),
    )
    if completed.returncode != 0:
        raise CapabilityError("CODEX_PROVIDER_EXECUTION_FAILED")
    raw = completed.stdout.decode("utf-8", errors="replace").strip()
    if len(raw) > settings.max_patch_chars:
        raise CapabilityError("CODEX_PROVIDER_OUTPUT_TOO_LARGE")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CapabilityError("CODEX_PROVIDER_OUTPUT_NOT_JSON") from exc
    if not isinstance(result, dict):
        raise CapabilityError("CODEX_PROVIDER_OUTPUT_NOT_OBJECT")
    changed = result.get("changed_files")
    patch = result.get("unified_diff")
    if not isinstance(changed, list) or not all(isinstance(x, str) for x in changed):
        raise CapabilityError("CODEX_PROVIDER_CHANGED_FILES_INVALID")
    if not isinstance(patch, str):
        raise CapabilityError("CODEX_PROVIDER_PATCH_INVALID")
    return {
        "provider": "codex-cli",
        "mode": "READ_ONLY_PATCH_PROPOSAL",
        "before_head": head,
        "changed_files": changed,
        "unified_diff": patch,
        "summary": str(result.get("summary") or "")[:4000],
        "tests": result.get("tests") if isinstance(result.get("tests"), list) else [],
        "git_mutation_allowed": False,
    }
