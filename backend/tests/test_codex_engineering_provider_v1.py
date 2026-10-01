from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import palwakf_local_agents.codex_engineering_provider_v1 as mod
from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
    source_apply_patch_bounded,
)


def _ctx(
    root: Path,
    scope_paths: tuple[str, ...],
    *,
    state_dir: Path | None = None,
) -> CapabilityContextV1:
    return CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(root),),
        scope_paths=scope_paths,
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha="1" * 40,
        max_output_bytes=131072,
        state_dir=str(state_dir) if state_dir is not None else None,
    )


def test_codex_provider_invocation_is_read_only(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / "codex.exe"
    executable.write_bytes(b"pinned-codex")
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = mod.CodexEngineeringSettingsV1(
        executable=str(executable),
        expected_sha256=mod.hashlib.sha256(executable.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(mod, "_settings", lambda: settings)
    monkeypatch.setattr(mod, "_repo_from_context", lambda _ctx, _args: repo)
    resolved_home = tmp_path / ".codex"
    monkeypatch.setattr(
        mod,
        "_resolve_codex_home",
        lambda _settings, _executable: resolved_home,
    )

    reads = iter(["1" * 40, "task/SOVEREIGN-CHANNEL-TEST", ""])
    monkeypatch.setattr(mod, "_git_read", lambda *_args: next(reads))
    captured: dict[str, object] = {}

    def runner(argv, **kwargs):
        captured["argv"] = list(argv)
        captured["kwargs"] = kwargs
        payload = {
            "summary": "bounded proposal",
            "changed_files": ["backend/src/example.py"],
            "unified_diff": "--- a/backend/src/example.py\n+++ b/backend/src/example.py\n",
            "tests": ["pytest"],
        }
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(payload).encode(),
            stderr=b"",
        )

    result = mod.codex_patch_proposal(
        _ctx(repo, ("backend/src",)),
        {"repo_root": str(repo), "prompt": "Propose one bounded edit."},
        runner=runner,
    )
    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "--sandbox" in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in argv
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    count = int(env["GIT_CONFIG_COUNT"])
    assert env[f"GIT_CONFIG_KEY_{count - 1}"] == "safe.directory"
    assert env[f"GIT_CONFIG_VALUE_{count - 1}"] == str(repo)
    assert env[f"GIT_CONFIG_VALUE_{count - 1}"] != "*"
    assert env["CODEX_HOME"] == str(resolved_home)
    assert result["git_mutation_allowed"] is False
    assert result["mode"] == "READ_ONLY_PATCH_PROPOSAL"


def _init_repo(path: Path) -> str:
    subprocess.run(["git", "init", "-b", "task/SOVEREIGN-CHANNEL-TEST"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "PalWakf Test"], cwd=path, check=True)
    target = path / "src" / "allowed.txt"
    target.parent.mkdir()
    target.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", "src/allowed.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=path, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def test_executor_applies_patch_without_mutating_git_refs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    head = _init_repo(repo)
    ctx = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(repo),),
        scope_paths=("src",),
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha=head,
        max_output_bytes=131072,
    )
    patch = (
        "--- a/src/allowed.txt\n"
        "+++ b/src/allowed.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    result = source_apply_patch_bounded(
        ctx,
        {
            "repo_root": str(repo),
            "paths": ["src/allowed.txt"],
            "unified_diff": patch,
        },
    )
    assert (repo / "src" / "allowed.txt").read_text(encoding="utf-8") == "after\n"
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip() == head
    assert result["git_refs_mutated"] is False


def test_patch_outside_scope_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    head = _init_repo(repo)
    ctx = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(repo),),
        scope_paths=("src",),
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha=head,
        max_output_bytes=131072,
    )
    patch = (
        "--- a/README.md\n"
        "+++ b/README.md\n"
        "@@ -0,0 +1 @@\n"
        "+forbidden\n"
    )
    with pytest.raises(CapabilityError, match="PATCH_SCOPE_WIDENING_DENIED"):
        source_apply_patch_bounded(
            ctx,
            {
                "repo_root": str(repo),
                "paths": ["README.md"],
                "unified_diff": patch,
            },
        )


def _write_proposal_artifact(
    state_dir: Path,
    *,
    before_head: str,
    changed_files: list[str],
    patch: str,
) -> tuple[str, str]:
    artifact_id = "a" * 32
    root = state_dir / "capability-results"
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_id": "palwakf.capability_result.codex_patch.v1",
        "task_id": "codex-artifact-test",
        "capability_id": "engineering.codex.patch_proposal",
        "result": {
            "provider": "codex-cli",
            "mode": "READ_ONLY_PATCH_PROPOSAL",
            "before_head": before_head,
            "changed_files": changed_files,
            "unified_diff": patch,
            "summary": "proposal",
            "tests": [],
            "git_mutation_allowed": False,
        },
    }
    data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    (root / f"{artifact_id}.json").write_bytes(data)
    return f"local-result://{artifact_id}/{digest}", digest


def test_executor_applies_verified_codex_proposal_artifact(tmp_path: Path) -> None:
    repo = tmp_path / "repo-artifact"
    repo.mkdir()
    head = _init_repo(repo)
    state_dir = tmp_path / "state"
    patch = (
        "--- a/src/allowed.txt\n"
        "+++ b/src/allowed.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after-artifact\n"
    )
    proposal_ref, proposal_sha = _write_proposal_artifact(
        state_dir,
        before_head=head,
        changed_files=["src/allowed.txt"],
        patch=patch,
    )
    ctx = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(repo),),
        scope_paths=("src",),
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha=head,
        max_output_bytes=131072,
        state_dir=str(state_dir),
    )
    result = source_apply_patch_bounded(
        ctx,
        {
            "repo_root": str(repo),
            "paths": ["src/allowed.txt"],
            "proposal_ref": proposal_ref,
            "proposal_sha256": proposal_sha,
        },
    )
    assert (repo / "src" / "allowed.txt").read_text(encoding="utf-8") == "after-artifact\n"
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
    ).strip() == head
    assert result["git_refs_mutated"] is False
    assert result["proposal_sha256"] == proposal_sha


def test_tampered_codex_proposal_hash_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo-tampered"
    repo.mkdir()
    head = _init_repo(repo)
    state_dir = tmp_path / "state-tampered"
    patch = (
        "--- a/src/allowed.txt\n"
        "+++ b/src/allowed.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    proposal_ref, _ = _write_proposal_artifact(
        state_dir,
        before_head=head,
        changed_files=["src/allowed.txt"],
        patch=patch,
    )
    artifact_id = proposal_ref.split("/")[2]
    fake = "0" * 64
    fake_ref = f"local-result://{artifact_id}/{fake}"
    ctx = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(repo),),
        scope_paths=("src",),
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha=head,
        state_dir=str(state_dir),
    )
    with pytest.raises(
        CapabilityError,
        match="PROPOSAL_ARTIFACT_HASH_MISMATCH",
    ):
        source_apply_patch_bounded(
            ctx,
            {
                "repo_root": str(repo),
                "paths": ["src/allowed.txt"],
                "proposal_ref": fake_ref,
                "proposal_sha256": fake,
            },
        )


def test_codex_proposal_changed_files_must_match_explicit_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo-path-mismatch"
    repo.mkdir()
    head = _init_repo(repo)
    state_dir = tmp_path / "state-path-mismatch"
    patch = (
        "--- a/src/allowed.txt\n"
        "+++ b/src/allowed.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    proposal_ref, proposal_sha = _write_proposal_artifact(
        state_dir,
        before_head=head,
        changed_files=["src/other.txt"],
        patch=patch,
    )
    ctx = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/example",
        allowed_roots=(str(repo),),
        scope_paths=("src",),
        task_branch="task/SOVEREIGN-CHANNEL-TEST",
        expected_base_sha=head,
        state_dir=str(state_dir),
    )
    with pytest.raises(
        CapabilityError,
        match="PROPOSAL_CHANGED_FILES_MISMATCH",
    ):
        source_apply_patch_bounded(
            ctx,
            {
                "repo_root": str(repo),
                "paths": ["src/allowed.txt"],
                "proposal_ref": proposal_ref,
                "proposal_sha256": proposal_sha,
            },
        )


def test_codex_env_removes_api_key_fallbacks(monkeypatch, tmp_path: Path) -> None:
    executable = tmp_path / "codex.exe"
    executable.write_bytes(b"pinned-codex")
    repo = tmp_path / "repo"
    repo.mkdir()
    resolved_home = tmp_path / ".codex"
    settings = mod.CodexEngineeringSettingsV1(
        executable=str(executable),
        expected_sha256=mod.hashlib.sha256(executable.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        mod,
        "_resolve_codex_home",
        lambda _settings, _executable: resolved_home,
    )
    first = "OPENAI" + "_API_KEY"
    second = "CODEX" + "_API_KEY"
    monkeypatch.setenv(first, "must-not-pass")
    monkeypatch.setenv(second, "must-not-pass")

    env = mod._codex_env(settings, executable, repo)

    assert env["CODEX_HOME"] == str(resolved_home)
    assert first not in env
    assert second not in env
    count = int(env["GIT_CONFIG_COUNT"])
    assert env[f"GIT_CONFIG_KEY_{count - 1}"] == "safe.directory"
    assert env[f"GIT_CONFIG_VALUE_{count - 1}"] == str(repo)
