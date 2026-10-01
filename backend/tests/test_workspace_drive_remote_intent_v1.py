from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import palwakf_local_agents.workspace_drive_remote_intent_v1 as mod
from palwakf_local_agents.workspace_drive_remote_intent_v1 import (
    DriveClientInboxV1,
    DriveRemoteIntentError,
    RcloneDriveRemoteIntentSettingsV1,
    RcloneWorkspaceDriveRemoteIntentTransportV1,
)


def settings(tmp_path: Path) -> RcloneDriveRemoteIntentSettingsV1:
    return RcloneDriveRemoteIntentSettingsV1(
        rclone_executable="rclone.exe",
        rclone_config_path=str(tmp_path / "rclone.conf"),
        remote_name="palwakf",
        client_inboxes=(
            DriveClientInboxV1(client_id="chatgpt", inbox_path="RemoteIntent/ChatGPT"),
            DriveClientInboxV1(client_id="mind", inbox_path="RemoteIntent/Mind"),
            DriveClientInboxV1(client_id="agentic", inbox_path="RemoteIntent/Agentic"),
        ),
        results_path="RemoteIntent/Results",
        archive_path="RemoteIntent/Archive",
        state_dir=str(tmp_path / "state"),
        authority_python="python.exe",
        authority_cli_path=str(tmp_path / "authority.py"),
        authority_src_path=str(tmp_path / "workspace-src"),
        authority_key_path=str(tmp_path / "workspace.dpapi"),
        authority_key_id="workspace-sovereign-v1",
        command_timeout_seconds=20,
    )


class FakeRclone:
    def __init__(self, *, listing=None, intent_text: str | None = None):
        self.calls: list[list[str]] = []
        self.listing = listing or []
        self.intent_text = intent_text

    def __call__(self, argv: list[str], timeout: int):
        del timeout
        self.calls.append(list(argv))
        verb_index = argv.index("--config") + 2
        verb = argv[verb_index]
        args = argv[verb_index + 1 :]
        if verb == "lsjson":
            return subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(self.listing).encode(), stderr=b""
            )
        if verb == "copyto":
            source, target = args[0], args[1]
            if source.startswith("palwakf:") and self.intent_text is not None:
                Path(target).write_text(self.intent_text, encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        if verb == "moveto":
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        raise AssertionError(f"unexpected rclone verb: {verb}")


def valid_intent(client_id: str = "chatgpt") -> str:
    return json.dumps(
        {
            "schema_id": "palwakf.remote_intent.v1",
            "client_id": client_id,
            "payload": {"task_id": "TASK-001"},
        }
    )


def install_successful_authority(monkeypatch, executor_id: str = "Futuer-IT"):
    def fake_run(argv, **kwargs):
        del kwargs
        output = Path(argv[argv.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "contract_version": "1.0",
                    "executor_id": executor_id,
                    "task_id": "TASK-001",
                }
            ),
            encoding="utf-8",
         )
        return subprocess.CompletedProcess(argv, 0, stdout=b"{}", stderr=b"")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)


def test_folder_bound_identity_rejects_payload_impersonation(tmp_path):
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(settings(tmp_path))
    with pytest.raises(
        DriveRemoteIntentError, match="REMOTE_INTENT_CLIENT_ID_MISMATCH"
    ):
        transport._parse_remote_intent(valid_intent("mind"), "chatgpt")


def test_malformed_json_fails_closed(tmp_path):
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(settings(tmp_path))
    with pytest.raises(DriveRemoteIntentError, match="REMOTE_INTENT_JSON_INVALID"):
        transport._parse_remote_intent("{not-json", "chatgpt")


def test_signer_failure_fails_closed(tmp_path, monkeypatch):
    runner = FakeRclone(
        listing=[{"Path": "intent.json", "ID": "drive-id-1"}],
        intent_text=valid_intent(),
    )
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(
        settings(tmp_path), runner=runner
    )

    def rejected(argv, **kwargs):
        del kwargs
        return subprocess.CompletedProcess(argv, 7, stdout=b"", stderr=b"rejected")

    monkeypatch.setattr(mod.subprocess, "run", rejected)
    with pytest.raises(DriveRemoteIntentError, match="WORKSPACE_AUTHORITY_REJECTED"):
        transport.claim_task(executor_id="Futuer-IT")


def test_claim_binds_identity_and_returns_signed_envelope(tmp_path, monkeypatch):
    runner = FakeRclone(
        listing=[{"Path": "intent.json", "ID": "drive-id-2"}],
        intent_text=valid_intent(),
    )
    install_successful_authority(monkeypatch)
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(
        settings(tmp_path), runner=runner
    )
    claimed = transport.claim_task(executor_id="Futuer-IT")
    assert claimed is not None
    assert claimed["client_id"] == "chatgpt"
    assert claimed["envelope"]["executor_id"] == "Futuer-IT"


def test_duplicate_is_suppressed_after_terminal_ack(tmp_path, monkeypatch):
    runner = FakeRclone(
        listing=[{"Path": "intent.json", "ID": "drive-id-3"}],
        intent_text=valid_intent(),
    )
    install_successful_authority(monkeypatch)
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(
        settings(tmp_path), runner=runner
    )
    claimed = transport.claim_task(executor_id="Futuer-IT")
    assert claimed is not None
    transport.ack_task(claimed, status="COMPLETED")
    assert transport.claim_task(executor_id="Futuer-IT") is None


def test_result_publication_and_archive_use_fixed_rclone_verbs(tmp_path, monkeypatch):
    runner = FakeRclone(
        listing=[{"Path": "intent.json", "ID": "drive-id-4"}],
        intent_text=valid_intent(),
    )
    install_successful_authority(monkeypatch)
    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(
        settings(tmp_path), runner=runner
    )
    claimed = transport.claim_task(executor_id="Futuer-IT")
    assert claimed is not None
    transport.publish_result(
        claimed,
        {"task_id": "TASK-001", "exit_state": "COMPLETED"},
    )
    transport.ack_task(claimed, status="COMPLETED")
    verbs = []
    for call in runner.calls:
        idx = call.index("--config") + 2
        verbs.append(call[idx])
    assert set(verbs) <= {"lsjson", "copyto", "moveto"}
    assert "copyto" in verbs
    assert "moveto" in verbs
    assert all("--config" in call for call in runner.calls)


def test_rclone_failure_is_redacted_and_fail_closed(tmp_path):
    def failed(argv, timeout):
        del timeout
        return subprocess.CompletedProcess(
            argv, 9, stdout=b"", stderr=b"secret-token"
        )

    transport = RcloneWorkspaceDriveRemoteIntentTransportV1(
        settings(tmp_path), runner=failed
     )
    with pytest.raises(
        DriveRemoteIntentError, match="RCLONE_LSJSON_FAILED"
    ) as exc:
        transport.claim_task(executor_id="Futuer-IT")
    assert "secret-token" not in str(exc.value)
