from pathlib import Path
import subprocess
import pytest

from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
    _git_argv,
    default_capability_registry_v1,
)


def ctx(tmp_path: Path):
    return CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="repo",
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(tmp_path),),
        task_branch="task/AGENTIC-P3-OUTBOUND-LOCAL-EXECUTOR-V1",
        expected_base_sha="a"*40,
    )


def test_registry_preserves_legacy_names_but_unknown_mutators_are_not_admitted():
    reg = default_capability_registry_v1()
    assert reg.resolve("mesh_hostname").capability_id == "device.hostname"
    with pytest.raises(CapabilityError):
        reg.resolve("bounded_powershell")


def test_file_read_rejects_path_escape(tmp_path):
    reg = default_capability_registry_v1()
    with pytest.raises(CapabilityError, match="PATH_OUTSIDE_ALLOWED_ROOTS"):
        reg.resolve("file_read").handler(ctx(tmp_path), {"path": "/etc/hosts"})


def test_git_stage_rejects_add_dot(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git","init"], cwd=repo, check=True, capture_output=True)
    with pytest.raises(CapabilityError, match="UNSAFE_STAGE_PATH"):
        default_capability_registry_v1().resolve("git.stage_paths").handler(ctx(tmp_path), {"repo_root":str(repo),"paths":["."]})


def test_git_safe_directory_is_scoped_to_exact_repo(tmp_path):
    repo = (tmp_path / "repo").resolve()
    argv = _git_argv(repo, "status", "--porcelain=v1")
    assert argv[:3] == ["git", "-c", f"safe.directory={repo}"]
    assert "safe.directory=*" not in argv


def test_git_commit_uses_executor_identity_without_global_config(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "checkout", "-b", "task/AGENTIC-P3-OUTBOUND-LOCAL-EXECUTOR-V1"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    target = repo / "note.txt"
    target.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    target.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "add", "note.txt"], cwd=repo, check=True, capture_output=True)
    result = default_capability_registry_v1().resolve("git.commit").handler(
        ctx(tmp_path),
        {"repo_root": str(repo), "message": "uat commit"},
    )
    assert result["commit_sha"]


def test_git_push_uses_protected_noninteractive_auth(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    repo.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    context = CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="repo",
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(repo),),
        task_branch="task/AGENTIC-P3-OUTBOUND-LOCAL-EXECUTOR-V1",
        expected_base_sha="b"*40,
        state_dir=str(state_dir),
    )
    calls = []

    def fake_run(argv, *, cwd, timeout=120, max_bytes=131072, env=None):
        calls.append((list(argv), env))
        if "branch" in argv:
            return {
                "exit_code": 0,
                "stdout": context.task_branch + "\n",
                "stderr": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
            }
        assert "push" in argv
        assert env is not None
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "Never"
        assert env["PALWAKF_GIT_TOKEN"] == "test-protected-token"
        assert Path(env["GIT_ASKPASS"]).is_file()
        return {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setattr(
        "palwakf_local_agents.outbound_capabilities_v1._run",
        fake_run,
    )
    monkeypatch.setattr(
        "palwakf_local_agents.outbound_capabilities_v1.read_windows_protected_text",
        lambda _path: "test-protected-token",
    )
    result = default_capability_registry_v1().resolve(
        "git.push_task_branch"
    ).handler(
        context,
        {"repo_root": str(repo), "branch": context.task_branch},
    )
    push_argv, push_env = calls[-1]
    assert "credential.helper=" in push_argv
    assert "test-protected-token" not in push_argv
    assert result["auth_mode"] == "PROTECTED_TOKEN_ASKPASS_NONINTERACTIVE"
    assert result["force"] is False
    assert push_env is not None
