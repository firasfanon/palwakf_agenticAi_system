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
