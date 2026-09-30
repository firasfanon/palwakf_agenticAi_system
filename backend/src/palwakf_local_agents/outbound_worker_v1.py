from __future__ import annotations

import json
import os
import signal
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.github_issue_transport_v1 import (
    GitHubIssueTransportSettingsV1,
    GitHubIssueTransportV1,
    TransportError,
)
from palwakf_local_agents.outbound_capabilities_v1 import default_capability_registry_v1
from palwakf_local_agents.outbound_contracts_v1 import Ed25519AuthorityVerifierV1, TaskEnvelopeV1
from palwakf_local_agents.outbound_local_executor_v1 import ExecutorSettingsV1, PalWakfOutboundLocalExecutorV1


class WorkerConfigV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executor: ExecutorSettingsV1
    transport: GitHubIssueTransportSettingsV1
    authority_public_keys_b64: dict[str, str] = Field(default_factory=dict)
    authority_public_keys_path: str | None = (
        r"C:\ProgramData\PalWakf\outbound_executor_v1\authority-keys.json"
    )
    poll_seconds: int = Field(default=15, ge=5, le=300)
    heartbeat_seconds: int = Field(default=60, ge=30, le=3600)

    def effective_authority_public_keys(self) -> dict[str, str]:
        keys = dict(self.authority_public_keys_b64)
        path = self.authority_public_keys_path
        if not path:
            if not keys:
                raise RuntimeError("AUTHORITY_PUBLIC_KEY_STORE_EMPTY")
            return keys
        target = Path(path)
        if not target.is_file():
            if not keys:
                raise RuntimeError("AUTHORITY_PUBLIC_KEY_STORE_EMPTY")
            return keys
        try:
            extra = json.loads(target.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("AUTHORITY_PUBLIC_KEY_STORE_INVALID") from exc
        if not isinstance(extra, dict) or not all(
            isinstance(key_id, str) and isinstance(value, str)
            for key_id, value in extra.items()
        ):
            raise RuntimeError("AUTHORITY_PUBLIC_KEY_STORE_INVALID")
        for key_id, value in extra.items():
            prior = keys.get(key_id)
            if prior is not None and prior != value:
                raise RuntimeError(f"AUTHORITY_PUBLIC_KEY_CONFLICT:{key_id}")
            keys[key_id] = value
        if not keys:
            raise RuntimeError("AUTHORITY_PUBLIC_KEY_STORE_EMPTY")
        return keys


class OutboundWorkerV1:
    def __init__(self, config: WorkerConfigV1):
        self.config = config
        self.transport = GitHubIssueTransportV1(config.transport)
        self.executor = PalWakfOutboundLocalExecutorV1(
            settings=config.executor,
            authority_verifier=Ed25519AuthorityVerifierV1(
                config.effective_authority_public_keys()
            ),
            registry=default_capability_registry_v1(),
        )
        self._stop = threading.Event()
        self._transport_degraded = False
        self.runtime_transport_audit_path = Path(config.executor.state_dir) / "transport-runtime.jsonl"

    def stop(self) -> None:
        self._stop.set()

    def _record_transport_event(self, event: str, error: Exception | None = None) -> None:
        path = getattr(self, "runtime_transport_audit_path", None)
        if path is None:
            return
        payload = {
            "event": event,
            "at": datetime.now(UTC).isoformat(),
            "executor_id": self.config.executor.executor_id,
        }
        if error is not None:
            payload["error"] = f"{type(error).__name__}:{str(error)[:300]}"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _mark_transport_failure(self, exc: TransportError) -> None:
        self._transport_degraded = True
        self._record_transport_event("TRANSPORT_ERROR", exc)

    def _mark_transport_success(self) -> None:
        if self._transport_degraded:
            self._record_transport_event("TRANSPORT_RECOVERED")
            self._transport_degraded = False

    def run(self) -> None:
        last_heartbeat = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now - last_heartbeat >= self.config.heartbeat_seconds:
                try:
                    self.transport.publish_heartbeat({
                        "executor_id": self.config.executor.executor_id,
                        "executor_version": "1.0.0-task",
                        "service_state": "RUNNING",
                        "last_seen": datetime.now(UTC).isoformat(),
                        "transport_state": "OUTBOUND_POLLING",
                    })
                    last_heartbeat = now
                    self._mark_transport_success()
                except TransportError as exc:
                    self._mark_transport_failure(exc)
                    self._stop.wait(self.config.poll_seconds)
                    continue

            try:
                claimed = self.transport.claim_task(executor_id=self.config.executor.executor_id)
                self._mark_transport_success()
            except TransportError as exc:
                self._mark_transport_failure(exc)
                self._stop.wait(self.config.poll_seconds)
                continue
            if claimed is None:
                self._stop.wait(self.config.poll_seconds)
                continue

            try:
                envelope = TaskEnvelopeV1.model_validate(self.transport.read_envelope(claimed))
                evidence = self.executor.execute(envelope, transport_adapter=self.transport.transport_id)
            except Exception as exc:
                try:
                    self.transport.release_or_fail(
                        claimed,
                        reason=f"{type(exc).__name__}:{str(exc)[:300]}",
                    )
                except TransportError:
                    pass
                self._stop.wait(self.config.poll_seconds)
                continue

            try:
                self.transport.publish_result(claimed, evidence.model_dump(mode="json"))
                self.transport.ack_task(claimed, status=evidence.exit_state)
            except TransportError as exc:
                self._mark_transport_failure(exc)
                # Keep the worker alive through transient network loss. The open
                # issue will be reclaimed after recovery; the local ledger then
                # returns the existing evidence without re-running the handler.
                self._stop.wait(self.config.poll_seconds)


def load_worker_config(path: str) -> WorkerConfigV1:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return WorkerConfigV1.model_validate(data)


def run_worker_from_env() -> None:
    path = os.environ.get("PALWAKF_EXECUTOR_CONFIG")
    if not path:
        raise RuntimeError("PALWAKF_EXECUTOR_CONFIG_NOT_SET")
    worker = OutboundWorkerV1(load_worker_config(path))
    signal.signal(signal.SIGTERM, lambda *_: worker.stop())
    signal.signal(signal.SIGINT, lambda *_: worker.stop())
    worker.run()


if __name__ == "__main__":
    run_worker_from_env()
