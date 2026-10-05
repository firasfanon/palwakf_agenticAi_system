import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import palwakf_local_agents.governed_runtime_maintenance_v1 as mod
from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityError,
    default_capability_registry_v1,
    runtime_maintenance_handler,
)


def _ctx(tmp_path: Path, head: str = "a" * 40):
    return SimpleNamespace(
        state_dir=str(tmp_path / "state"),
        expected_base_sha=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(tmp_path),),
    )


def _configure_tmp(monkeypatch, tmp_path: Path):
    repo = tmp_path / "repo"
    source = repo / mod.SOURCE_RELATIVE
    source.parent.mkdir(parents=True)
    source.write_text("candidate", encoding="utf-8")
    (repo / ".git").mkdir()

    target = tmp_path / "runtime.py"
    target.write_text("current", encoding="utf-8")
    drive = tmp_path / "drive"
    drive.mkdir()

    monkeypatch.setattr(mod, "TARGET_MODULE", target)
    monkeypatch.setattr(mod, "DRIVE_ROOT", drive)
    monkeypatch.setattr(mod, "SECRET_TEMP_ROOT", drive / "rclone-secret-temp")
    monkeypatch.setattr(mod, "_service_state", lambda: "RUNNING")
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")
    python_home = tmp_path / "python-home"
    python_home.mkdir()
    interpreter = python_home / "python.exe"
    interpreter.write_bytes(b"trusted-python")
    monkeypatch.setattr(mod.sys, "base_prefix", str(python_home))

    head = "a" * 40

    def fixed(argv, *, timeout=60):
        del timeout
        if argv == ["git", "-c", f"safe.directory={repo.resolve()}", "-C", str(repo.resolve()), "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, stdout=(head + "\n").encode(), stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    return repo, source, target, drive, head


def test_registry_admits_only_named_runtime_maintenance_capability():
    descriptor = default_capability_registry_v1().resolve(
        "runtime.maintenance.promote_bounded_v1"
    )
    assert descriptor.mutation_class == "SERVICE_MUTATION"
    assert descriptor.idempotency_class == "STATEFUL_GOVERNED"


def test_prepare_exact_hashes_and_backup(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    result = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    assert result["source_sha256"] == mod._sha256(source)
    assert result["runtime_pre_sha256"] == mod._sha256(target)
    assert result["backup_sha256"] == mod._sha256(target)
    assert Path(result["plan_path"]).is_file()


def test_prepare_rejects_wrong_source_hash(tmp_path, monkeypatch):
    repo, _source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="SOURCE_HASH_MISMATCH"):
        mod.prepare_plan(
            repo_root=str(repo),
            state_dir=str(tmp_path / "state"),
            expected_source_sha256="0" * 64,
            expected_runtime_sha256=mod._sha256(target),
            expected_head=head,
            allowed_roots=(str(tmp_path),),
            scope_paths=(str(repo / mod.SOURCE_RELATIVE),),
        )


def test_prepare_rejects_wrong_runtime_hash(tmp_path, monkeypatch):
    repo, source, _target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="RUNTIME_HASH_MISMATCH"):
        mod.prepare_plan(
            repo_root=str(repo),
            state_dir=str(tmp_path / "state"),
            expected_source_sha256=mod._sha256(source),
            expected_runtime_sha256="0" * 64,
            expected_head=head,
            allowed_roots=(str(tmp_path),),
            scope_paths=(str(source),),
        )


def test_capability_rejects_arbitrary_argument(tmp_path):
    ctx = _ctx(tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="ARGUMENT_NOT_ALLOWED"):
        mod.runtime_maintenance_capability(
            ctx, {"operation": "status", "command": "powershell.exe"}
        )


def test_capability_rejects_unknown_operation(tmp_path):
    with pytest.raises(mod.RuntimeMaintenanceError, match="OPERATION_NOT_ALLOWED"):
        mod.runtime_maintenance_capability(_ctx(tmp_path), {"operation": "shell"})


def test_execute_rejects_tampered_target_path(tmp_path, monkeypatch):
    repo, source, target, _drive, _head = _configure_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "TARGET_MODULE", target)
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "schema_id": mod.PLAN_SCHEMA,
                "plan_id": "x",
                "service_name": mod.SERVICE_NAME,
                "source_path": str(source),
                "target_path": str(tmp_path / "other.py"),
                "expected_source_sha256": mod._sha256(source),
                "expected_runtime_sha256": mod._sha256(target),
                "backup_path": str(target),
                "receipt_path": str(tmp_path / "receipt.json"),
                "python_interpreter_path": str((tmp_path / "python-home" / "python.exe").resolve()),
                "python_interpreter_sha256": mod._sha256(tmp_path / "python-home" / "python.exe"),
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)
    with pytest.raises(mod.RuntimeMaintenanceError, match="TARGET_NOT_ALLOWLISTED"):
        mod.execute_plan_file(str(plan))


def test_residue_unknown_fails_closed(tmp_path, monkeypatch):
    _repo, _source, _target, drive, _head = _configure_tmp(monkeypatch, tmp_path)
    unknown = drive / "palwakf-rclone-config-bad"
    unknown.mkdir()
    (unknown / "rclone.conf").write_text("placeholder", encoding="utf-8")
    (unknown / "extra.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(mod.RuntimeMaintenanceError, match="UNKNOWN_FAIL_CLOSED"):
        mod._classify_residue()


def test_handler_redacts_internal_exception_type(tmp_path):
    with pytest.raises(CapabilityError, match="MAINTENANCE_ARGUMENT_NOT_ALLOWED"):
        runtime_maintenance_handler(
            _ctx(tmp_path),
            {"operation": "status", "unexpected": True},
        )


def test_prepare_uses_command_scoped_exact_safe_directory(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    seen = []

    def fixed(argv, *, timeout=60):
        del timeout
        seen.append(list(argv))
        if argv[-2:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(argv, 0, stdout=(head + "\n").encode(), stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    git_calls = [argv for argv in seen if argv and argv[0] == "git"]
    assert git_calls == [[
        "git",
        "-c",
        f"safe.directory={repo.resolve()}",
        "-C",
        str(repo.resolve()),
        "rev-parse",
        "HEAD",
    ]]
    assert "*" not in " ".join(git_calls[0])
    assert "config" not in git_calls[0]


def test_prepare_rejects_repo_outside_allowed_roots(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="REPO_OUTSIDE_ALLOWED_ROOTS"):
        mod.prepare_plan(
            repo_root=str(repo),
            state_dir=str(tmp_path / "state"),
            expected_source_sha256=mod._sha256(source),
            expected_runtime_sha256=mod._sha256(target),
            expected_head=head,
            allowed_roots=(str(tmp_path / "different-root"),),
            scope_paths=(str(source),),
        )


def test_prepare_rejects_source_outside_scope(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="SOURCE_SCOPE_DENIED"):
        mod.prepare_plan(
            repo_root=str(repo),
            state_dir=str(tmp_path / "state"),
            expected_source_sha256=mod._sha256(source),
            expected_runtime_sha256=mod._sha256(target),
            expected_head=head,
            allowed_roots=(str(tmp_path),),
            scope_paths=(str(tmp_path / "unrelated"),),
        )


def test_prepare_rejects_wrong_head_with_scoped_git_trust(tmp_path, monkeypatch):
    repo, source, target, _drive, _head = _configure_tmp(monkeypatch, tmp_path)
    with pytest.raises(mod.RuntimeMaintenanceError, match="HEAD_DRIFT"):
        mod.prepare_plan(
            repo_root=str(repo),
            state_dir=str(tmp_path / "state"),
            expected_source_sha256=mod._sha256(source),
            expected_runtime_sha256=mod._sha256(target),
            expected_head="b" * 40,
            allowed_roots=(str(tmp_path),),
            scope_paths=(str(source),),
        )


def test_runtime_handler_passes_context_boundaries(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    ctx = SimpleNamespace(
        state_dir=str(tmp_path / "state"),
        expected_base_sha=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    result = mod.runtime_maintenance_capability(
        ctx,
        {
            "operation": "prepare",
            "repo_root": str(repo),
            "expected_source_sha256": mod._sha256(source),
            "expected_runtime_sha256": mod._sha256(target),
        },
    )
    assert result["source_sha256"] == mod._sha256(source)

def test_prepare_binds_verified_python_interpreter_identity(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    result = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    interpreter = (tmp_path / "python-home" / "python.exe").resolve()
    assert result["python_interpreter_path"] == str(interpreter)
    assert result["python_interpreter_sha256"] == mod._sha256(interpreter)
    plan = json.loads(Path(result["plan_path"]).read_text(encoding="utf-8"))
    assert plan["python_interpreter_path"] == str(interpreter)
    assert plan["python_interpreter_sha256"] == mod._sha256(interpreter)


def test_launch_uses_verified_interpreter_and_isolated_mode(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    prepared = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    monkeypatch.setattr(mod, "_canonical_under", lambda *_args: True)
    seen = {}

    class DummyProcess:
        pid = 4321

    def popen(argv, **kwargs):
        seen["argv"] = list(argv)
        seen["kwargs"] = dict(kwargs)
        return DummyProcess()

    monkeypatch.setattr(mod.subprocess, "Popen", popen)
    result = mod.launch_helper(repo_root=str(repo), plan_path=prepared["plan_path"])
    interpreter = str((tmp_path / "python-home" / "python.exe").resolve())
    assert seen["argv"][:4] == [
        interpreter,
        "-I",
        "-m",
        "palwakf_local_agents.governed_runtime_maintenance_v1",
    ]
    assert seen["kwargs"]["shell"] is False
    assert result["helper_pid"] == 4321


def test_launch_rejects_tampered_interpreter_path(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    prepared = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    plan_path = Path(prepared["plan_path"])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    other = tmp_path / "other-python.exe"
    other.write_bytes(b"other")
    plan["python_interpreter_path"] = str(other.resolve())
    plan["python_interpreter_sha256"] = mod._sha256(other)
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(mod, "_canonical_under", lambda *_args: True)
    with pytest.raises(mod.RuntimeMaintenanceError, match="PYTHON_INTERPRETER_NOT_ALLOWLISTED"):
        mod.launch_helper(repo_root=str(repo), plan_path=str(plan_path))


def test_launch_rejects_interpreter_hash_drift(tmp_path, monkeypatch):
    repo, source, target, _drive, head = _configure_tmp(monkeypatch, tmp_path)
    prepared = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    interpreter = tmp_path / "python-home" / "python.exe"
    interpreter.write_bytes(b"tampered")
    monkeypatch.setattr(mod, "_canonical_under", lambda *_args: True)
    with pytest.raises(mod.RuntimeMaintenanceError, match="PYTHON_INTERPRETER_HASH_MISMATCH"):
        mod.launch_helper(repo_root=str(repo), plan_path=prepared["plan_path"])


def test_caller_cannot_supply_python_interpreter_path(tmp_path):
    with pytest.raises(mod.RuntimeMaintenanceError, match="ARGUMENT_NOT_ALLOWED"):
        mod.runtime_maintenance_capability(
            _ctx(tmp_path),
            {
                "operation": "status",
                "python_interpreter_path": r"C:\Other\python.exe",
            },
        )


def _prepared_plan_for_execute(tmp_path, monkeypatch):
    repo, source, target, drive, head = _configure_tmp(monkeypatch, tmp_path)
    prepared = mod.prepare_plan(
        repo_root=str(repo),
        state_dir=str(tmp_path / "state"),
        expected_source_sha256=mod._sha256(source),
        expected_runtime_sha256=mod._sha256(target),
        expected_head=head,
        allowed_roots=(str(tmp_path),),
        scope_paths=(str(source),),
    )
    monkeypatch.chdir(repo)
    return repo, source, target, drive, Path(prepared["plan_path"]), Path(prepared["receipt_path"])


def test_execute_stop_first_success_and_running_at_exit(tmp_path, monkeypatch):
    _repo, source, target, drive, plan, receipt = _prepared_plan_for_execute(tmp_path, monkeypatch)
    states = iter(["RUNNING", "STOP_PENDING", "STOPPED", "RUNNING", "RUNNING"])
    monkeypatch.setattr(mod, "_service_state", lambda: next(states, "RUNNING"))
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")
    calls = []

    def fixed(argv, *, timeout=60):
        del timeout
        calls.append(list(argv))
        if argv[:2] == ["sc.exe", "stop"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv[:2] == ["sc.exe", "start"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv and argv[0] == "icacls.exe":
            return subprocess.CompletedProcess(argv, 0, stdout=b"SYSTEM:(F) Administrators:(F)", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    stale = drive / "palwakf-rclone-config-stale"
    stale.mkdir()
    (stale / "rclone.conf").write_text("placeholder", encoding="utf-8")
    result = mod.execute_plan_file(str(plan))
    assert result["status"] == "PASS"
    assert result["service_state"] == "RUNNING"
    assert result["stale_residue_removed"] == 1
    assert not stale.exists()
    assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    assert receipt.is_file()
    stop_index = next(i for i, argv in enumerate(calls) if argv[:2] == ["sc.exe", "stop"])
    start_index = next(i for i, argv in enumerate(calls) if argv[:2] == ["sc.exe", "start"])
    assert stop_index < start_index


def test_stop_timeout_makes_no_runtime_or_residue_mutation_and_recovers(tmp_path, monkeypatch):
    _repo, _source, target, drive, plan, _receipt = _prepared_plan_for_execute(tmp_path, monkeypatch)
    runtime_before = mod._sha256(target)
    stale = drive / "palwakf-rclone-config-stale"
    stale.mkdir()
    (stale / "rclone.conf").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(mod, "_service_state", lambda: "RUNNING")
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")

    def wait_service(expected, *, timeout_seconds=90):
        del timeout_seconds
        if expected == "STOPPED":
            raise mod.RuntimeMaintenanceError("MAINTENANCE_SERVICE_STOP_TIMEOUT")
        return ["RUNNING"]

    monkeypatch.setattr(mod, "_wait_service", wait_service)

    def fixed(argv, *, timeout=60):
        del timeout
        if argv[:2] == ["sc.exe", "stop"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    result = mod.execute_plan_file(str(plan))
    assert result["status"] == "FAIL"
    assert result["error_code"] == "MAINTENANCE_SERVICE_STOP_TIMEOUT"
    assert result["service_recovery"] == "NOT_NEEDED"
    assert result["service_state_after_recovery"] == "RUNNING"
    assert mod._sha256(target) == runtime_before
    assert stale.exists()


@pytest.mark.parametrize(
    ("failing_stage", "expected_code"),
    [
        ("POST_STOP_REVALIDATION", "MAINTENANCE_SOURCE_HASH_MISMATCH"),
        ("PROMOTE_RUNTIME", "MAINTENANCE_RUNTIME_POST_HASH_MISMATCH"),
        ("HARDEN_SECRET_TEMP_ACL", "MAINTENANCE_ACL_ENFORCEMENT_FAILED"),
        ("CLEAN_STALE_RESIDUE", "MAINTENANCE_RESIDUE_CLEANUP_INCOMPLETE"),
    ],
)
def test_failure_after_stop_rolls_back_and_recovers_service(
    tmp_path, monkeypatch, failing_stage, expected_code
):
    _repo, source, target, _drive, plan, _receipt = _prepared_plan_for_execute(tmp_path, monkeypatch)
    runtime_before = mod._sha256(target)
    states = iter(["RUNNING", "STOPPED", "STOPPED", "RUNNING"])
    monkeypatch.setattr(mod, "_service_state", lambda: next(states, "RUNNING"))
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")

    def fixed(argv, *, timeout=60):
        del timeout
        if argv[:2] == ["sc.exe", "stop"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv[:2] == ["sc.exe", "start"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv and argv[0] == "icacls.exe":
            if failing_stage == "HARDEN_SECRET_TEMP_ACL":
                return subprocess.CompletedProcess(argv, 5, stdout=b"", stderr=b"")
            return subprocess.CompletedProcess(argv, 0, stdout=b"SYSTEM:(F) Administrators:(F)", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    original_sha = mod._sha256

    if failing_stage == "POST_STOP_REVALIDATION":
        calls = {"source": 0}

        def drift_sha(path):
            if Path(path).resolve() == source.resolve():
                calls["source"] += 1
                if calls["source"] >= 2:
                    return "0" * 64
            return original_sha(path)
        monkeypatch.setattr(mod, "_sha256", drift_sha)
    elif failing_stage == "PROMOTE_RUNTIME":
        def bad_post_hash(path):
            value = original_sha(path)
            if Path(path).resolve() == target.resolve() and value == original_sha(source):
                return "0" * 64
            return value
        monkeypatch.setattr(mod, "_sha256", bad_post_hash)
    elif failing_stage == "CLEAN_STALE_RESIDUE":
        monkeypatch.setattr(
            mod,
            "_cleanup_stale_residue",
            lambda: (_ for _ in ()).throw(mod.RuntimeMaintenanceError("MAINTENANCE_RESIDUE_CLEANUP_INCOMPLETE")),
        )

    result = mod.execute_plan_file(str(plan))
    assert result["status"] in {"FAIL", "FAIL_RECOVERY_FAILED"}
    assert result["error_code"] == expected_code
    assert result["service_state_after_recovery"] == "RUNNING"
    if failing_stage != "PROMOTE_RUNTIME":
        assert mod._sha256(target) == runtime_before or result["runtime_rollback"] in {"PASS", "NOT_NEEDED"}


def test_start_failure_rolls_back_and_records_recovery(tmp_path, monkeypatch):
    _repo, source, target, _drive, plan, _receipt = _prepared_plan_for_execute(tmp_path, monkeypatch)
    runtime_before = mod._sha256(target)
    states = iter(["RUNNING", "STOPPED", "STOPPED", "STOPPED", "RUNNING", "RUNNING"])
    monkeypatch.setattr(mod, "_service_state", lambda: next(states, "RUNNING"))
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")
    starts = {"count": 0}

    def fixed(argv, *, timeout=60):
        del timeout
        if argv[:2] == ["sc.exe", "stop"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv[:2] == ["sc.exe", "start"]:
            starts["count"] += 1
            code = 5 if starts["count"] == 1 else 0
            return subprocess.CompletedProcess(argv, code, stdout=b"", stderr=b"")
        if argv and argv[0] == "icacls.exe":
            return subprocess.CompletedProcess(argv, 0, stdout=b"SYSTEM:(F) Administrators:(F)", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    result = mod.execute_plan_file(str(plan))
    assert result["status"] == "FAIL"
    assert result["error_code"] == "MAINTENANCE_SERVICE_START_FAILED"
    assert result["service_recovery"] == "PASS"
    assert result["service_state_after_recovery"] == "RUNNING"
    assert mod._sha256(target) == runtime_before


def test_recovery_failure_is_explicit(tmp_path, monkeypatch):
    _repo, _source, _target, _drive, plan, _receipt = _prepared_plan_for_execute(tmp_path, monkeypatch)
    states = iter(["RUNNING", "STOPPED", "STOPPED", "STOPPED", "STOPPED"])
    monkeypatch.setattr(mod, "_service_state", lambda: next(states, "STOPPED"))
    monkeypatch.setattr(mod, "_service_start_name", lambda: "LocalSystem")
    monkeypatch.setattr(mod, "_set_secret_temp_acl", lambda: (_ for _ in ()).throw(mod.RuntimeMaintenanceError("MAINTENANCE_ACL_ENFORCEMENT_FAILED")))

    def fixed(argv, *, timeout=60):
        del timeout
        if argv[:2] == ["sc.exe", "stop"]:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if argv[:2] == ["sc.exe", "start"]:
            return subprocess.CompletedProcess(argv, 5, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(mod, "_run_fixed", fixed)
    result = mod.execute_plan_file(str(plan))
    assert result["status"] == "FAIL_RECOVERY_FAILED"
    assert result["service_recovery"] == "FAIL"


def test_service_name_is_not_caller_supplied(tmp_path):
    with pytest.raises(mod.RuntimeMaintenanceError, match="ARGUMENT_NOT_ALLOWED"):
        mod.runtime_maintenance_capability(
            _ctx(tmp_path),
            {"operation": "status", "service_name": "OtherService"},
        )