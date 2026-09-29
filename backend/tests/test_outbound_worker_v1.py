from __future__ import annotations

from types import SimpleNamespace

from palwakf_local_agents.github_issue_transport_v1 import TransportError
from palwakf_local_agents.outbound_worker_v1 import OutboundWorkerV1


class _StopAfterWait:
    def __init__(self):
        self.wait_calls = 0

    def is_set(self):
        return self.wait_calls > 0

    def wait(self, _seconds):
        self.wait_calls += 1
        return True


def _worker_with(transport):
    worker = object.__new__(OutboundWorkerV1)
    worker.config = SimpleNamespace(
        heartbeat_seconds=60,
        poll_seconds=5,
        executor=SimpleNamespace(executor_id="DESKTOP-S5A0JSB"),
    )
    worker.transport = transport
    worker.executor = SimpleNamespace()
    worker._stop = _StopAfterWait()
    return worker


def test_worker_survives_heartbeat_transport_failure():
    class Transport:
        transport_id = "github-issues-v1"

        def publish_heartbeat(self, _payload):
            raise TransportError("offline")

    worker = _worker_with(Transport())
    worker.run()
    assert worker._stop.wait_calls == 1


def test_worker_survives_claim_poll_transport_failure():
    class Transport:
        transport_id = "github-issues-v1"

        def publish_heartbeat(self, _payload):
            return None

        def claim_task(self, *, executor_id):
            assert executor_id == "DESKTOP-S5A0JSB"
            raise TransportError("offline")

    worker = _worker_with(Transport())
    worker.run()
    assert worker._stop.wait_calls == 1
