from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.github_capabilities_v1 import (
    GitHubCapabilityError,
    _current_branch,
    _require_repo_binding,
    _rooted_repo,
)


class CodexProviderError(RuntimeError):
    pass


class CodexProviderSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executable: str
    expected_version: str = "codex-cli 0.159.1"
    max_duration_seconds: int = Field(default=900, ge=30, le=3600)
    max_prompt_chars: int = Field(default=20000, ge=100, le=100000)
    max_result_bytes: int = Field(default=131072, ge=4096, le=1048576)


class CodexCapabilityContext(Protocol):
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
    timeout: int,
    stdin_text: str | None = None,
    env: Mapping[str, str] | None = None,
    max_bytes: int = 131072,
) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=str(cwd),
        shell=False,
        input=stdin_text.encode("utf-8") if stdin_text is not None else None,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=dict(env) if env is not None else None,
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


def _safe_prompt(settings: CodexProviderSettingsV1, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CodexProviderError("CODEX_PROMPT_REQUIRED")
    if len(value) > settings.max_prompt_chars:
        raise CodexProviderError("CODEX_PROMPT_TOO_LARGE")
    return value


def _safe_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    return env


def _status_paths(repo: Path) -> tuple[str, ...]:
    result = _run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=repo,
        timeout=30,
        max_bytes=1048576,
    )
    if result["exit_code"] != 0:
        raise CodexProviderError("CODEX_GIT_STATUS_FAILED")
    raw = result["stdout"]
    if not raw:
        return ()
    output: list[str] = []
    fields = raw.split("\x00")
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4:
            raise CodexProviderError("CODEX_GIT_STATUS_INVALID")
        status = entry[:2]
        path = entry[3:]
        if status[0] in {"R", "C"} and index < len(fields):
            replacement = fields[index]
            index += 1
            if replacement:
                output.append(replacement)
        output.append(path)
    return tuple(dict.fromkeys(output))


def _scope_roots(ctx: CodexCapabilityContext, repo: Path) -> tuple[Path, ...]:
    roots: list[Path] = []
    for item in ctx.scope_paths:
        raw = Path(item)
        target = raw.resolve() if raw.is_absolute() else (repo / raw).resolve()
        if target != repo and repo not in target.parents:
            raise CodexProviderError("CODEX_SIGNED_SCOPE_OUTSIDE_REPOSITORY")
        roots.append(target)
    return tuple(roots)


def _path_within_scopes(path: str, *, repo: Path, scopes: tuple[Path, ...]) -> bool:
    target = (repo / path).resolve()
    return any(target == scope or scope in target.parents for scope in scopes)


def _restore_clean_anchor(repo: Path, anchor: str) -> None:
    restore = _run(
        ["git", "restore", "--source", anchor, "--staged", "--worktree", "--", "."],
        cwd=repo,
        timeout=120,
    )
    if restore["exit_code"] != 0:
        raise CodexProviderError("CODEX_ROLLBACK_TRACKED_FAILED")
    untracked = _run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo,
        timeout=30,
        max_bytes=1048576,
    )
    if untracked["exit_code"] != 0:
        raise CodexProviderError("CODEX_ROLLBACK_UNTRACKED_ENUM_FAILED")
    for relative in (item for item in untracked["stdout"].split("\x00") if item):
        target = (repo / relative).resolve()
        if target != repo and repo not in target.parents:
            raise CodexProviderError("CODEX_ROLLBACK_PATH_ESCAPE")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


class CodexEngineeringProviderV1:
    provider_id = "codex-cli-app-server-v1"

    def __init__(self, settings: CodexProviderSettingsV1) -> None:
        self.settings = settings

    def readiness(self) -> Mapping[str, Any]:
        executable = Path(self.settings.executable)
        if not executable.is_file():
            return {
                "provider_id": self.provider_id,
                "state": "NOT_READY",
                "reason": "CODEX_EXECUTABLE_NOT_FOUND",
            }
        version = _run(
            [str(executable), "--version"],
            cwd=executable.parent,
            timeout=30,
            env=_safe_environment(),
            max_bytes=4096,
        )
        if version["exit_code"] != 0:
            return {
                "provider_id": self.provider_id,
                "state": "NOT_READY",
                "reason": "CODEX_VERSION_READ_FAILED",
            }
        observed = version["stdout"].strip()
        if observed != self.settings.expected_version:
            return {
                "provider_id": self.provider_id,
                "state": "NOT_READY",
                "reason": "CODEX_VERSION_MISMATCH",
                "observed_version": observed,
            }
        login = _run(
            [str(executable), "login", "status"],
            cwd=executable.parent,
            timeout=30,
            env=_safe_environment(),
            max_bytes=4096,
        )
        login_ready = login["exit_code"] == 0 and "Logged in" in login["stdout"]
        return {
            "provider_id": self.provider_id,
            "state": "READY" if login_ready else "AUTH_REQUIRED",
            "version": observed,
            "chatgpt_login_ready": login_ready,
            "normal_openai_api_key_used": False,
            "normal_codex_api_key_used": False,
        }

    def execute(
        self,
        ctx: CodexCapabilityContext,
        args: Mapping[str, Any],
        *,
        mode: str,
    ) -> Mapping[str, Any]:
        repo = _rooted_repo(str(args.get("repo_root", "")), ctx.allowed_roots)
        try:
            _require_repo_binding(ctx, repo)
        except GitHubCapabilityError as exc:
            raise CodexProviderError(str(exc)) from exc
        if _current_branch(ctx, repo) != ctx.task_branch:
            raise CodexProviderError("CODEX_CURRENT_BRANCH_MISMATCH")
        head = _run(["git", "rev-parse", "HEAD"], cwd=repo, timeout=30)["stdout"].strip()
        if mode == "edit_bounded" and head.lower() != ctx.expected_base_sha.lower():
            raise CodexProviderError("CODEX_BASE_HEAD_DRIFT")
        before = _status_paths(repo)
        if before:
            raise CodexProviderError("CODEX_WORKTREE_MUST_START_CLEAN")
        prompt = _safe_prompt(self.settings, args.get("prompt"))
        sandbox = "workspace-write" if mode == "edit_bounded" else "read-only"
        scopes = _scope_roots(ctx, repo)
        if mode == "edit_bounded" and not scopes:
            raise CodexProviderError("CODEX_EDIT_SCOPE_REQUIRED")
        executable = Path(self.settings.executable)
        if not executable.is_file():
            raise CodexProviderError("CODEX_EXECUTABLE_NOT_FOUND")
        with tempfile.TemporaryDirectory(prefix="palwakf-codex-") as temp:
            output_path = Path(temp) / "last-message.txt"
            command = [
                str(executable),
                "exec",
                "-C",
                str(repo),
                "--sandbox",
                sandbox,
                "--ephemeral",
                "--color",
                "never",
                "-o",
                str(output_path),
                "-",
            ]
            result = _run(
                command,
                cwd=repo,
                timeout=min(
                    int(args.get("timeout_seconds", self.settings.max_duration_seconds)),
                    self.settings.max_duration_seconds,
                ),
                stdin_text=prompt,
                env=_safe_environment(),
                max_bytes=self.settings.max_result_bytes,
            )
            if result["exit_code"] != 0:
                if mode == "edit_bounded":
                    _restore_clean_anchor(repo, head)
                raise CodexProviderError("CODEX_EXEC_FAILED")
            message = (
                output_path.read_text(encoding="utf-8", errors="replace")
                if output_path.is_file()
                else ""
            )
        changed = _status_paths(repo)
        if mode != "edit_bounded" and changed:
            _restore_clean_anchor(repo, head)
            raise CodexProviderError("CODEX_READ_ONLY_MODE_MUTATED_WORKTREE")
        if mode == "edit_bounded":
            violations = [
                item
                for item in changed
                if not _path_within_scopes(item, repo=repo, scopes=scopes)
            ]
            if violations:
                _restore_clean_anchor(repo, head)
                raise CodexProviderError("CODEX_SCOPE_VIOLATION")
        return {
            "provider_id": self.provider_id,
            "mode": mode,
            "repository_id": ctx.repository_id,
            "task_branch": ctx.task_branch,
            "base_head": head,
            "changed_paths": list(changed),
            "last_message": message[: self.settings.max_result_bytes],
            "normal_openai_api_key_used": False,
            "normal_codex_api_key_used": False,
        }


class UnavailableCodexEngineeringProviderV1:
    provider_id = "codex-unavailable-v1"

    def readiness(self) -> Mapping[str, Any]:
        return {
            "provider_id": self.provider_id,
            "state": "NOT_CONFIGURED",
        }

    def execute(self, ctx, args, *, mode: str):
        raise CodexProviderError("CODEX_PROVIDER_NOT_CONFIGURED")


def extra_codex_capabilities_v1(provider=None):
    from palwakf_local_agents.outbound_capabilities_v1 import (
        CapabilityDescriptorV1,
        CapabilityError,
    )

    bound = provider or UnavailableCodexEngineeringProviderV1()

    def adapt(mode: str):
        def wrapped(ctx, args):
            try:
                if mode == "readiness":
                    return bound.readiness()
                return bound.execute(ctx, args, mode=mode)
            except (CodexProviderError, GitHubCapabilityError) as exc:
                raise CapabilityError(str(exc)) from exc
        return wrapped

    return (
        CapabilityDescriptorV1(
            "engineering.codex.readiness",
            "READ_ONLY",
            adapt("readiness"),
        ),
        CapabilityDescriptorV1(
            "engineering.codex.analyze",
            "READ_ONLY",
            adapt("analyze"),
        ),
        CapabilityDescriptorV1(
            "engineering.codex.plan",
            "READ_ONLY",
            adapt("plan"),
        ),
        CapabilityDescriptorV1(
            "engineering.codex.review_diff",
            "READ_ONLY",
            adapt("review_diff"),
        ),
        CapabilityDescriptorV1(
            "engineering.codex.edit_bounded",
            "SOURCE_WRITE",
            adapt("edit_bounded"),
            idempotency_class="STATEFUL_GOVERNED",
        ),
        CapabilityDescriptorV1(
            "engineering.codex.test",
            "TEMP_MUTATION",
            adapt("test"),
        ),
        CapabilityDescriptorV1(
            "engineering.codex.debug",
            "TEMP_MUTATION",
            adapt("debug"),
        ),
    )


def codex_provider_from_env() -> CodexEngineeringProviderV1 | None:
    executable = os.environ.get("PALWAKF_CODEX_EXECUTABLE")
    if not executable:
        return None
    expected = os.environ.get("PALWAKF_CODEX_EXPECTED_VERSION", "codex-cli 0.159.1")
    return CodexEngineeringProviderV1(
        CodexProviderSettingsV1(
            executable=executable,
            expected_version=expected,
        )
    )
