from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.github_issue_transport_v1 import TaskTransport, TransportError


class LocalSpoolTransportSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str = r"C:\ProgramData\PalWakf\sovereign_channel_v1"


class LocalSpoolTransportV1:
    transport_id = "local-spool-v1"

    def __init__(self, settings: LocalSpoolTransportSettingsV1) -> None:
        self.settings = settings
        self.root = Path(settings.root)
        self.inbox = self.root / "inbox"
        self.claimed = self.root / "claimed"
        self.results = self.root / "results"
        self.progress = self.root / "progress"
        self.acks = self.root / "acks"
        self.failed = self.root / "failed"
        for directory in (
            self.inbox,
            self.claimed,
            self.results,
            self.progress,
            self.acks,
            self.failed,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TransportError("LOCAL_SPOOL_JSON_INVALID") from exc
        if not isinstance(value, dict):
            raise TransportError("LOCAL_SPOOL_OBJECT_REQUIRED")
        return value

    @staticmethod
    def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, path)

    @staticmethod
    def _safe_task_id(value: object) -> str:
        task_id = str(value or "")
        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-"
        if not task_id or any(char not in allowed for char in task_id):
            raise TransportError("LOCAL_SPOOL_TASK_ID_INVALID")
        return task_id

    def health(self) -> Mapping[str, Any]:
        return {
            "transport_id": self.transport_id,
            "status": "HEALTHY",
            "root": str(self.root),
        }

    def claim_task(self, *, executor_id: str) -> Mapping[str, Any] | None:
        for candidate in sorted(self.inbox.glob("*.json"), key=lambda item: item.name):
            try:
                envelope = self._load(candidate)
            except TransportError:
                continue
            if envelope.get("executor_id") != executor_id:
                continue
            task_id = self._safe_task_id(envelope.get("task_id"))
            claimed_path = self.claimed / f"{task_id}.json"
            try:
                os.replace(candidate, claimed_path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise TransportError("LOCAL_SPOOL_CLAIM_FAILED") from exc
            return {
                "task_id": task_id,
                "claimed_path": str(claimed_path),
                "envelope": envelope,
            }
        return None

    def read_envelope(self, claimed: Mapping[str, Any]) -> Mapping[str, Any]:
        envelope = claimed.get("envelope")
        if not isinstance(envelope, dict):
            raise TransportError("LOCAL_SPOOL_CLAIMED_ENVELOPE_MISSING")
        return envelope

    def ack_task(self, claimed: Mapping[str, Any], *, status: str) -> None:
        task_id = self._safe_task_id(claimed.get("task_id"))
        self._atomic_json(
            self.acks / f"{task_id}.json",
            {"task_id": task_id, "status": status},
        )
        claimed_path = self.claimed / f"{task_id}.json"
        if claimed_path.exists():
            claimed_path.unlink()

    def publish_progress(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        task_id = self._safe_task_id(claimed.get("task_id"))
        self._atomic_json(self.progress / f"{task_id}.json", payload)

    def publish_result(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        task_id = self._safe_task_id(claimed.get("task_id"))
        self._atomic_json(self.results / f"{task_id}.json", payload)

    def publish_heartbeat(self, payload: Mapping[str, Any]) -> None:
        self._atomic_json(self.root / "heartbeat.json", payload)

    def release_or_fail(self, claimed: Mapping[str, Any], *, reason: str) -> None:
        task_id = self._safe_task_id(claimed.get("task_id"))
        claimed_path = self.claimed / f"{task_id}.json"
        if claimed_path.is_file():
            target = self.failed / f"{task_id}.json"
            try:
                os.replace(claimed_path, target)
            except OSError as exc:
                raise TransportError("LOCAL_SPOOL_FAIL_MOVE_FAILED") from exc
        self._atomic_json(
            self.failed / f"{task_id}.failure.json",
            {"task_id": task_id, "reason": reason[:300]},
        )


class CompositeTaskTransportV1:
    """One transport contract with deterministic failover and bounded backoff."""

    transport_id = "composite-outbound-v1"

    def __init__(
        self,
        transports: tuple[TaskTransport, ...],
        *,
        reconnect_min_seconds: int = 5,
        reconnect_max_seconds: int = 300,
    ) -> None:
        if not transports:
            raise ValueError("AT_LEAST_ONE_TRANSPORT_REQUIRED")
        if reconnect_min_seconds < 1 or reconnect_max_seconds < reconnect_min_seconds:
            raise ValueError("INVALID_RECONNECT_BOUNDS")
        ids = [getattr(item, "transport_id", "") for item in transports]
        if len(set(ids)) != len(ids) or any(not item for item in ids):
            raise ValueError("TRANSPORT_IDS_MUST_BE_UNIQUE")
        self.transports = transports
        self.reconnect_min_seconds = reconnect_min_seconds
        self.reconnect_max_seconds = reconnect_max_seconds
        self._failures: dict[str, int] = {item: 0 for item in ids}
        self._next_attempt: dict[str, float] = {item: 0.0 for item in ids}

    def _id(self, transport: TaskTransport) -> str:
        return str(getattr(transport, "transport_id"))

    def _ready(self, transport: TaskTransport) -> bool:
        return time.monotonic() >= self._next_attempt[self._id(transport)]

    def _success(self, transport: TaskTransport) -> None:
        key = self._id(transport)
        self._failures[key] = 0
        self._next_attempt[key] = 0.0

    def _failure(self, transport: TaskTransport) -> None:
        key = self._id(transport)
        failures = self._failures[key] + 1
        self._failures[key] = failures
        delay = min(
            self.reconnect_max_seconds,
            self.reconnect_min_seconds * (2 ** min(failures - 1, 10)),
        )
        self._next_attempt[key] = time.monotonic() + delay

    def health(self) -> Mapping[str, Any]:
        states: list[dict[str, Any]] = []
        any_healthy = False
        for transport in self.transports:
            if not self._ready(transport):
                states.append(
                    {
                        "transport_id": self._id(transport),
                        "status": "BACKOFF",
                        "failures": self._failures[self._id(transport)],
                    }
                )
                continue
            try:
                state = dict(transport.health())
                self._success(transport)
                any_healthy = True
            except TransportError as exc:
                self._failure(transport)
                state = {
                    "transport_id": self._id(transport),
                    "status": "DEGRADED",
                    "error": type(exc).__name__,
                }
            states.append(state)
        return {
            "transport_id": self.transport_id,
            "status": "HEALTHY" if any_healthy else "DEGRADED",
            "adapters": states,
        }

    def claim_task(self, *, executor_id: str) -> Mapping[str, Any] | None:
        attempted = 0
        failures = 0
        for transport in self.transports:
            if not self._ready(transport):
                continue
            attempted += 1
            try:
                claim = transport.claim_task(executor_id=executor_id)
                self._success(transport)
            except TransportError:
                failures += 1
                self._failure(transport)
                continue
            if claim is None:
                continue
            return {
                "_transport_id": self._id(transport),
                "_claim": dict(claim),
            }
        if attempted and failures == attempted:
            raise TransportError("ALL_TRANSPORTS_DEGRADED")
        return None

    def _route(self, claimed: Mapping[str, Any]) -> tuple[TaskTransport, Mapping[str, Any]]:
        transport_id = claimed.get("_transport_id")
        inner = claimed.get("_claim")
        if not isinstance(transport_id, str) or not isinstance(inner, Mapping):
            raise TransportError("COMPOSITE_CLAIM_INVALID")
        for transport in self.transports:
            if self._id(transport) == transport_id:
                return transport, inner
        raise TransportError("COMPOSITE_TRANSPORT_NOT_FOUND")

    def claim_transport_id(self, claimed: Mapping[str, Any]) -> str:
        transport, _ = self._route(claimed)
        return self._id(transport)

    def read_envelope(self, claimed: Mapping[str, Any]) -> Mapping[str, Any]:
        transport, inner = self._route(claimed)
        return transport.read_envelope(inner)

    def ack_task(self, claimed: Mapping[str, Any], *, status: str) -> None:
        transport, inner = self._route(claimed)
        transport.ack_task(inner, status=status)

    def publish_progress(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        transport, inner = self._route(claimed)
        transport.publish_progress(inner, payload)

    def publish_result(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        transport, inner = self._route(claimed)
        transport.publish_result(inner, payload)

    def publish_heartbeat(self, payload: Mapping[str, Any]) -> None:
        successful = 0
        for transport in self.transports:
            if not self._ready(transport):
                continue
            try:
                transport.publish_heartbeat(payload)
                self._success(transport)
                successful += 1
            except TransportError:
                self._failure(transport)
        if successful == 0 and all(not self._ready(item) for item in self.transports):
            raise TransportError("ALL_TRANSPORTS_IN_BACKOFF")

    def release_or_fail(self, claimed: Mapping[str, Any], *, reason: str) -> None:
        transport, inner = self._route(claimed)
        transport.release_or_fail(inner, reason=reason)
