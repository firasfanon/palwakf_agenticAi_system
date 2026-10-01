from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import palwakf_local_agents.workspace_drive_capabilities_v1 as mod
from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
)


def _ctx() -> CapabilityContextV1:
    return CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/palwakf_agenticAi_system",
        allowed_roots=(r"C:\Users\DELL\StudioProjects",),
        scope_paths=("drive://PalWakf/Knowledge",),
        task_branch="task/AGENTIC-SOVEREIGN-REMOTE-CHANNEL-V1",
        expected_base_sha="1" * 40,
        max_output_bytes=65536,
    )


def _config(monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "_config",
        lambda: (
            "rclone.exe",
            r"C:\ProgramData\PalWakf\rclone.conf",
            None,
            "palwakf",
            ("PalWakf",),
        ),
    )


def test_write_requires_revision_precondition(monkeypatch) -> None:
    _config(monkeypatch)
    with pytest.raises(
        CapabilityError,
        match="WORKSPACE_DRIVE_REVISION_PRECONDITION_REQUIRED",
    ):
        mod.workspace_drive_write_bounded(
            _ctx(),
            {
                "drive_path": "PalWakf/Knowledge/state.json",
                "content": "{}",
            },
        )


def test_scope_widening_fails_before_rclone(monkeypatch) -> None:
    _config(monkeypatch)
    with pytest.raises(
        CapabilityError,
        match="WORKSPACE_DRIVE_SCOPE_WIDENING_DENIED",
    ):
        mod.workspace_drive_read(
            _ctx(),
            {"drive_path": "PalWakf/Other/secret.txt"},
        )


def test_create_only_rejects_existing_target(monkeypatch) -> None:
    _config(monkeypatch)

    def fake_rclone(_exe, _config, _protected, _argv, **_kwargs):
        return subprocess.CompletedProcess([], 0, stdout=b"{}", stderr=b"")

    monkeypatch.setattr(mod, "_rclone", fake_rclone)

    with pytest.raises(
        CapabilityError,
        match="WORKSPACE_DRIVE_CREATE_TARGET_EXISTS",
    ):
        mod.workspace_drive_write_bounded(
            _ctx(),
            {
                "drive_path": "PalWakf/Knowledge/new.json",
                "content": "{}",
                "create_only": True,
            },
        )


def test_update_checks_sha_then_writes(monkeypatch, tmp_path: Path) -> None:
    _config(monkeypatch)
    old = b'{"v":1}'
    expected = hashlib.sha256(old).hexdigest()
    calls: list[list[str]] = []

    def fake_rclone(_exe, _config, _protected, argv, **_kwargs):
        calls.append(list(argv))
        if "lsjson" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=b"{}", stderr=b"")
        if "copyto" in argv:
            source_index = argv.index("copyto") + 1
            source = argv[source_index]
            target = argv[source_index + 1]
            if source.startswith("palwakf:"):
                Path(target).write_bytes(old)
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        raise AssertionError(argv)

    monkeypatch.setattr(mod, "_rclone", fake_rclone)

    result = mod.workspace_drive_write_bounded(
        _ctx(),
        {
            "drive_path": "PalWakf/Knowledge/state.json",
            "content": '{"v":2}',
            "expected_sha256": expected,
        },
    )

    assert result["revision_precondition_enforced"] is True
    assert result["sha256"] == hashlib.sha256(b'{"v":2}').hexdigest()
    assert any("lsjson" in call for call in calls)
    assert sum("copyto" in call for call in calls) == 2


def test_update_rejects_stale_sha(monkeypatch) -> None:
    _config(monkeypatch)
    old = b"current"

    def fake_rclone(_exe, _config, _protected, argv, **_kwargs):
        if "lsjson" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=b"{}", stderr=b"")
        if "copyto" in argv:
            idx = argv.index("copyto") + 1
            source, target = argv[idx], argv[idx + 1]
            if source.startswith("palwakf:"):
                Path(target).write_bytes(old)
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        raise AssertionError(argv)

    monkeypatch.setattr(mod, "_rclone", fake_rclone)
    with pytest.raises(
        CapabilityError,
        match="WORKSPACE_DRIVE_REVISION_PRECONDITION_FAILED",
    ):
        mod.workspace_drive_write_bounded(
            _ctx(),
            {
                "drive_path": "PalWakf/Knowledge/state.json",
                "content": "new",
                "expected_sha256": "0" * 64,
            },
        )
