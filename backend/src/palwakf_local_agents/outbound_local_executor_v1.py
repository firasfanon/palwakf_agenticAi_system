from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
    CapabilityRegistryV1,
)
from palwakf_local_agents.outbound_contracts_v1 import (
    AuthorityVerifier,
    EvidenceEnvelopeV1,
    TaskEnvelopeV1,
)


EXECUTOR_VERSION = "1.0.0-task"
POLICY_INVARIANTS = (
    "NO_ARBITRARY_SHELL",
    "NO_DIRECT_MAIN_MUTATION",
    "NO_FORCE_PUSH",
    "NO_BASELINE_PROMOTION",
    "NO_PRODUCTION_BY_DEFAULT",
    "NO_SHARED_DB_MUTATION",
    "TRANSPORT_IS_NOT_AUTHORITY",
)


class ExecutorSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executor_id: str
    repository_id: str
    allowed_repository_ids: tuple[str, ...] = Field(default=(), max_length=64)
    allowed_roots: tuple[str, ...] = Field(min_length=1, max_length=64)
    state_dir: str

    def repository_allowed(self, repository_id: str) -> bool:
        return repository_id in {self.repository_id, *self.allowed_repository_ids}
    max_output_bytes: int = Field(default=131072, ge=4096, le=1048576)


class LocalTaskLedgerV1:
    def __init__(self, db_path: str):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        with sqlite3.connect(self._db_path) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS task_ledger (
                    task_id TEXT PRIMARY KEY,
                    envelope_hash TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    nonce TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    evidence_json TEXT,
                    last_error TEXT
                )
                """
            )

    def existing_by_idempotency(self, key: str) -> Mapping[str, Any] | None:
        with sqlite3.connect(self._db_path) as db:
            row = db.execute(
                "SELECT task_id,envelope_hash,state,attempt_count,evidence_json,last_error FROM task_ledger WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "task_id": row[0], "envelope_hash": row[1], "state": row[2],
            "attempt_count": row[3], "evidence_json": row[4], "last_error": row[5]
        }

    def claim(self, envelope: TaskEnvelopeV1) -> int:
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self._db_path) as db:
            existing = db.execute(
                "SELECT attempt_count,envelope_hash FROM task_ledger WHERE task_id=?",
                (envelope.task_id,),
            ).fetchone()
            if existing is None:
                db.execute(
                    "INSERT INTO task_ledger(task_id,envelope_hash,idempotency_key,nonce,state,attempt_count,started_at) VALUES(?,?,?,?,?,?,?)",
                    (envelope.task_id,envelope.envelope_hash(),envelope.idempotency_key,envelope.nonce,"CLAIMED",1,now),
                )
                return 1
            if existing[1] != envelope.envelope_hash():
                raise RuntimeError("TASK_ID_REUSED_WITH_DIFFERENT_ENVELOPE")
            attempts = int(existing[0]) + 1
            db.execute(
                "UPDATE task_ledger SET state=?,attempt_count=?,started_at=?,last_error=NULL WHERE task_id=?",
                ("CLAIMED",attempts,now,envelope.task_id),
            )
            return attempts

    def finish(self, task_id: str, state: str, evidence: EvidenceEnvelopeV1 | None, error: str | None = None) -> None:
        with sqlite3.connect(self._db_path) as db:
            db.execute(
                "UPDATE task_ledger SET state=?,finished_at=?,evidence_json=?,last_error=? WHERE task_id=?",
                (state,datetime.now(UTC).isoformat(),evidence.model_dump_json() if evidence else None,error,task_id),
            )


class PalWakfOutboundLocalExecutorV1:
    def __init__(
        self,
        *,
        settings: ExecutorSettingsV1,
        authority_verifier: AuthorityVerifier,
        registry: CapabilityRegistryV1,
    ):
        self.settings = settings
        self.authority_verifier = authority_verifier
        self.registry = registry
        state_dir = Path(settings.state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = state_dir / "task-ledger.sqlite3"
        self.audit_path = state_dir / "audit.jsonl"
        self.ledger = LocalTaskLedgerV1(str(self.ledger_path))

    def _audit(self, payload: Mapping[str, Any]) -> None:
        safe = dict(payload)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str) + "\n")

    def _persist_codex_proposal_artifact(
        self,
        *,
        task_id: str,
        capability_id: str,
        result: Mapping[str, Any],
    ) -> tuple[str, str]:
        artifact_root = Path(self.settings.state_dir) / "capability-results"
        artifact_root.mkdir(parents=True, exist_ok=True)
        artifact_id = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:32]
        artifact_path = artifact_root / f"{artifact_id}.json"
        payload = {
            "schema_id": "palwakf.capability_result.codex_patch.v1",
            "task_id": task_id,
            "capability_id": capability_id,
            "result": dict(result),
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        if len(encoded) > self.settings.max_output_bytes * 4:
            raise CapabilityError("CODEX_PROPOSAL_ARTIFACT_TOO_LARGE")
        digest = hashlib.sha256(encoded).hexdigest()
        temp = artifact_path.with_suffix(".tmp")
        temp.write_bytes(encoded)
        os.replace(temp, artifact_path)
        return digest, f"local-result://{artifact_id}/{digest}"

    def execute(self, envelope: TaskEnvelopeV1, *, transport_adapter: str) -> EvidenceEnvelopeV1:
        started = datetime.now(UTC)
        started_clock = time.monotonic()
        attempt_count = 1
        blockers: list[str] = []
        before_anchor: str | None = None
        after_anchor: str | None = None
        stdout_summary: str | None = None
        stderr_summary: str | None = None
        artifact_hashes: tuple[str, ...] = ()
        checkpoint_ref: str | None = None
        exit_state = "FAILED"
        verification_state = "NOT_RUN"
        authority_verdict = "NOT_VERIFIED"
        lease_verdict = "NOT_VERIFIED"
        preflight_verdict = "NOT_RUN"

        prior = self.ledger.existing_by_idempotency(envelope.idempotency_key)
        if prior and prior.get("evidence_json") and prior.get("state") == "COMPLETED":
            return EvidenceEnvelopeV1.model_validate_json(prior["evidence_json"])

        attempt_count = self.ledger.claim(envelope)
        try:
            now = datetime.now(UTC)
            if envelope.executor_id != self.settings.executor_id:
                blockers.append("EXECUTOR_ID_MISMATCH")
            if not self.settings.repository_allowed(envelope.repository_id):
                blockers.append("REPOSITORY_ID_MISMATCH")
            allowed, authority_blockers = self.authority_verifier.verify(envelope, now=now)
            blockers.extend(authority_blockers)
            authority_verdict = "PASS" if allowed else "FAIL"
            lease_verdict = "PASS" if not authority_blockers else "FAIL"
            if blockers:
                raise CapabilityError("AUTHORITY_OR_BINDING_REJECTED")

            descriptor = self.registry.resolve(envelope.requested_capability_id)
            if descriptor.mutation_class != envelope.mutation_class:
                blockers.append("CAPABILITY_MUTATION_CLASS_MISMATCH")
                raise CapabilityError("CAPABILITY_MUTATION_CLASS_MISMATCH")
            if envelope.expected_remote_head.lower() != envelope.expected_base_sha.lower():
                blockers.append("HEAD_DRIFT")
                raise CapabilityError("HEAD_DRIFT")
            preflight_verdict = "PASS"

            context = CapabilityContextV1(
                executor_id=self.settings.executor_id,
                repository_id=envelope.repository_id,
                allowed_roots=self.settings.allowed_roots,
                scope_paths=envelope.scope_paths,
                task_branch=envelope.task_branch,
                expected_base_sha=envelope.expected_base_sha,
                max_output_bytes=self.settings.max_output_bytes,
                state_dir=self.settings.state_dir,
            )
            result = dict(descriptor.handler(context, envelope.arguments))
            encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            stdout_summary = f"RESULT_SHA256={hashlib.sha256(encoded).hexdigest()};BYTES={len(encoded)}"
            if descriptor.capability_id == "engineering.codex.patch_proposal":
                artifact_sha256, checkpoint_ref = self._persist_codex_proposal_artifact(
                    task_id=envelope.task_id,
                    capability_id=descriptor.capability_id,
                    result=result,
                )
                artifact_hashes = (artifact_sha256,)
            if descriptor.capability_id == "c7r.phase_a":
                safe_summary = result.get("_evidence_summary")
                if not isinstance(safe_summary, str) or not safe_summary or len(safe_summary) > 1600:
                    raise CapabilityError("C7R_SAFE_EVIDENCE_SUMMARY_REQUIRED")
                forbidden_markers = (
                    "access_token",
                    "refresh_token",
                    "id_token",
                    "authorization-url",
                    "code_verifier",
                    "signature_b64",
                )
                lowered = safe_summary.casefold()
                if any(marker in lowered for marker in forbidden_markers):
                    raise CapabilityError("C7R_SAFE_EVIDENCE_SUMMARY_REJECTED")
                stdout_summary += ";SAFE=" + safe_summary
            exit_state = "COMPLETED"
            verification_state = "HANDLER_RETURNED"
        except Exception as exc:
            if not blockers:
                blockers.append(type(exc).__name__)
            stderr_summary = f"{type(exc).__name__}:{str(exc)[:300]}"
            binding_rejections = {
                "EXECUTOR_ID_MISMATCH",
                "REPOSITORY_ID_MISMATCH",
            }
            if authority_verdict == "FAIL" or binding_rejections.intersection(blockers):
                exit_state = "REJECTED"
            elif "HEAD_DRIFT" in blockers:
                exit_state = "DRIFTED"
            elif isinstance(exc, CapabilityError):
                exit_state = "BLOCKED"
            else:
                exit_state = "FAILED"
        finished = datetime.now(UTC)
        evidence = EvidenceEnvelopeV1(
            task_id=envelope.task_id,
            project_id=envelope.project_id,
            envelope_hash=envelope.envelope_hash(),
            authority_verdict=authority_verdict,
            lease_verdict=lease_verdict,
            preflight_verdict=preflight_verdict,
            capability_id=envelope.requested_capability_id,
            mutation_class=envelope.mutation_class,
            before_state_anchor=before_anchor,
            after_state_anchor=after_anchor,
            started_at=started,
            finished_at=finished,
            duration_ms=max(0, int((time.monotonic() - started_clock) * 1000)),
            executor_version=EXECUTOR_VERSION,
            transport_adapter=transport_adapter,
            attempt_count=attempt_count,
            exit_state=exit_state,
            verification_state=verification_state,
            artifact_hashes=artifact_hashes,
            stdout_hash_or_summary=stdout_summary,
            stderr_hash_or_summary=stderr_summary,
            checkpoint_ref=checkpoint_ref,
            blockers=tuple(dict.fromkeys(blockers)),
            policy_invariants=POLICY_INVARIANTS,
        )
        self.ledger.finish(envelope.task_id, exit_state, evidence, stderr_summary)
        self._audit({
            "task_id": envelope.task_id,
            "envelope_hash": envelope.envelope_hash(),
            "capability_id": envelope.requested_capability_id,
            "exit_state": exit_state,
            "blockers": evidence.blockers,
            "finished_at": finished.isoformat(),
        })
        return evidence
