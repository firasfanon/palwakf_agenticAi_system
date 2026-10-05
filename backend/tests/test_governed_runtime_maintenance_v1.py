from __future__ import annotations

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

    head = "a" * 40

    def fixed(argv, *, timeout=60):
        del timeout
        if argv[:4] == ["git", "-C", str(repo.resolve()), "rev-parse"]:
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
