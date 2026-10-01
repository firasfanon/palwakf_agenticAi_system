from __future__ import annotations

import json

import pytest

from palwakf_local_agents.github_issue_transport_v1 import TransportError
from palwakf_local_agents.local_spool_transport_v1 import (
    CompositeTaskTransportV1,
    LocalSpoolTransportSettingsV1,
    LocalSpoolTransportV1,
)


def _envelope(task_id: str = "TASK-001") -> dict[str, object]:
    return {
        "task_id": task_id,
        "executor_id": "Futuer-IT",
        "requested_capability_id": "health.check",
    }


def test_local_spool_claim_result_ack_round_trip(tmp_path) -> None:
    transport = LocalSpoolTransportV1(
        LocalSpoolTransportSettingsV1(root=str(tmp_path))
    )
    inbox = tmp_path / "inbox" / "TASK-001.json"
    inbox.write_text(json.dumps(_envelope()), encoding="utf-8")

    claim = transport.claim_task(executor_id="Futuer-IT")

    assert claim is not None
    assert not inbox.exists()
    assert (tmp_path / "claimed" / "TASK-001.json").exists()
    assert transport.read_envelope(claim)["task_id"] == "TASK-001"

    transport.publish_result(claim, {"exit_state": "COMPLETED"})
    transport.ack_task(claim, status="COMPLETED")

    result = json.loads(
        (tmp_path / "results" / "TASK-001.json").read_text(encoding="utf-8")
    )
    ack = json.loads(
        (tmp_path / "acks" / "TASK-001.json").read_text(encoding="utf-8")
    )
    assert result == {"exit_state": "COMPLETED"}
    assert ack["status"] == "COMPLETED"
    assert not (tmp_path / "claimed" / "TASK-001.json").exists()


def test_local_spool_ignores_tasks_for_other_executor(tmp_path) -> None:
    transport = LocalSpoolTransportV1(
        LocalSpoolTransportSettingsV1(root=str(tmp_path))
    )
    path = tmp_path / "inbox" / "TASK-001.json"
    path.write_text(
        json.dumps({**_envelope(), "executor_id": "OTHER"}),
        encoding="utf-8",
    )

    assert transport.claim_task(executor_id="Futuer-IT") is None
    assert path.exists()


def test_local_spool_release_moves_task_to_failed(tmp_path) -> None:
    transport = LocalSpoolTransportV1(
        LocalSpoolTransportSettingsV1(root=str(tmp_path))
    )
    path = tmp_path / "inbox" / "TASK-001.json"
    path.write_text(json.dumps(_envelope()), encoding="utf-8")
    claim = transport.claim_task(executor_id="Futuer-IT")
    assert claim is not None

    transport.release_or_fail(claim, reason="INVALID_ENVELOPE")

    assert (tmp_path / "failed" / "TASK-001.json").exists()
    failure = json.loads(
        (tmp_path / "failed" / "TASK-001.failure.json").read_text(
            encoding="utf-8"
        )
    )
    assert failure["reason"] == "INVALID_ENVELOPE"


class _FakeTransport:
    def __init__(self, transport_id: str, claims: list[object]) -> None:
        self.transport_id = transport_id
        self.claims = claims
        self.heartbeats = 0

    def health(self):
        return {"transport_id": self.transport_id, "status": "HEALTHY"}

    def claim_task(self, *, executor_id: str):
        if not self.claims:
            return None
        value = self.claims.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def read_envelope(self, claimed):
        return claimed["envelope"]

    def ack_task(self, claimed, *, status: str):
        claimed["ack"] = status

    def publish_progress(self, claimed, payload):
        claimed["progress"] = dict(payload)

    def publish_result(self, claimed, payload):
        claimed["result"] = dict(payload)

    def publish_heartbeat(self, payload):
        self.heartbeats += 1

    def release_or_fail(self, claimed, *, reason: str):
        claimed["failure"] = reason


def test_composite_transport_falls_through_degraded_adapter() -> None:
    first = _FakeTransport(
        "primary",
        [TransportError("network down")],
    )
    second_claim = {"envelope": _envelope()}
    second = _FakeTransport("fallback", [second_claim])
    composite = CompositeTaskTransportV1(
        (first, second),
        reconnect_min_seconds=1,
        reconnect_max_seconds=4,
    )

    claimed = composite.claim_task(executor_id="Futuer-IT")

    assert claimed is not None
    assert claimed["_transport_id"] == "fallback"
    assert composite.read_envelope(claimed)["task_id"] == "TASK-001"
    composite.publish_result(claimed, {"exit_state": "COMPLETED"})
    assert second_claim["result"]["exit_state"] == "COMPLETED"


def test_composite_transport_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="TRANSPORT_IDS_MUST_BE_UNIQUE"):
        CompositeTaskTransportV1(
            (_FakeTransport("same", []), _FakeTransport("same", []))
        )
