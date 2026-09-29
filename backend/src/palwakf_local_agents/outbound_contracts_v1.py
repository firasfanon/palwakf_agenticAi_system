from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Mapping, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator


MutationClass = Literal["READ_ONLY", "TEMP_MUTATION", "SOURCE_WRITE", "SERVICE_MUTATION"]


class AuthorityProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: Literal["ED25519"] = "ED25519"
    key_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{2,160}$")
    signature_b64: str = Field(min_length=40, max_length=256)


class ExecutionLeaseV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lease_id: str = Field(min_length=3, max_length=200)
    task_id: str
    project_id: str
    issuer_ref: str
    approval_class: str
    allowed_capability_ids: tuple[str, ...] = Field(min_length=1, max_length=64)
    allowed_mutation_classes: tuple[MutationClass, ...] = Field(min_length=1, max_length=4)
    scope_paths: tuple[str, ...] = Field(default=(), max_length=128)
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    branch: str = Field(min_length=5, max_length=240)
    issued_at: datetime
    expires_at: datetime
    revocation_state: Literal["ACTIVE", "REVOKED"] = "ACTIVE"

    @model_validator(mode="after")
    def validate_lease(self) -> "ExecutionLeaseV1":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("LEASE_TIMESTAMPS_MUST_BE_TIMEZONE_AWARE")
        if self.expires_at <= self.issued_at:
            raise ValueError("LEASE_EXPIRY_MUST_FOLLOW_ISSUE")
        if len(set(self.allowed_capability_ids)) != len(self.allowed_capability_ids):
            raise ValueError("LEASE_CAPABILITY_IDS_MUST_BE_UNIQUE")
        if len(set(self.scope_paths)) != len(self.scope_paths):
            raise ValueError("LEASE_SCOPE_PATHS_MUST_BE_UNIQUE")
        return self


class TaskEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["1.0"] = "1.0"
    task_id: str = Field(min_length=3, max_length=200)
    project_id: str = Field(min_length=3, max_length=200)
    project_aliases: tuple[str, ...] = Field(default=(), max_length=32)
    repository_id: str = Field(min_length=3, max_length=240)
    executor_id: str = Field(min_length=3, max_length=160)
    task_type: str = Field(min_length=3, max_length=160)
    mutation_class: MutationClass
    requested_capability_id: str = Field(min_length=3, max_length=160)
    arguments: dict[str, Any] = Field(default_factory=dict)
    authority_ref: str = Field(min_length=3, max_length=500)
    execution_lease: ExecutionLeaseV1
    expected_remote_head: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    expected_base_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    task_branch: str = Field(min_length=5, max_length=240)
    scope_paths: tuple[str, ...] = Field(default=(), max_length=128)
    prohibited_actions: tuple[str, ...] = Field(default=(), max_length=128)
    idempotency_key: str = Field(min_length=8, max_length=240)
    nonce: str = Field(min_length=8, max_length=240)
    issued_at: datetime
    expires_at: datetime
    max_duration_seconds: int = Field(ge=1, le=7200)
    evidence_requirements: tuple[str, ...] = Field(default=(), max_length=64)
    transport_metadata: dict[str, Any] = Field(default_factory=dict)
    authority_proof: AuthorityProofV1
    correlation_id: str | None = Field(default=None, max_length=200)
    checkpoint_id: str | None = Field(default=None, max_length=200)
    depends_on_task_ids: tuple[str, ...] = Field(default=(), max_length=64)
    model_provider_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_envelope(self) -> "TaskEnvelopeV1":
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("TASK_TIMESTAMPS_MUST_BE_TIMEZONE_AWARE")
        if self.expires_at <= self.issued_at:
            raise ValueError("TASK_EXPIRY_MUST_FOLLOW_ISSUE")
        lease = self.execution_lease
        if lease.task_id != self.task_id:
            raise ValueError("LEASE_TASK_MISMATCH")
        if lease.project_id != self.project_id:
            raise ValueError("LEASE_PROJECT_MISMATCH")
        if lease.branch != self.task_branch:
            raise ValueError("LEASE_BRANCH_MISMATCH")
        if lease.base_sha.lower() != self.expected_base_sha.lower():
            raise ValueError("LEASE_BASE_MISMATCH")
        if self.requested_capability_id not in lease.allowed_capability_ids:
            raise ValueError("LEASE_CAPABILITY_NOT_ALLOWED")
        if self.mutation_class not in lease.allowed_mutation_classes:
            raise ValueError("LEASE_MUTATION_CLASS_NOT_ALLOWED")
        if self.mutation_class in {"SOURCE_WRITE", "SERVICE_MUTATION"} and not self.task_branch.startswith("task/"):
            raise ValueError("MUTATION_REQUIRES_TASK_BRANCH")
        if self.mutation_class != "READ_ONLY" and not self.scope_paths:
            raise ValueError("MUTATION_SCOPE_REQUIRED")
        return self

    def signed_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data.pop("authority_proof", None)
        data.pop("transport_metadata", None)
        data.pop("model_provider_metadata", None)
        return data

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.signed_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def envelope_hash(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class EvidenceEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_version: Literal["1.0"] = "1.0"
    task_id: str
    project_id: str
    envelope_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_verdict: str
    lease_verdict: str
    preflight_verdict: str
    capability_id: str
    mutation_class: MutationClass
    before_state_anchor: str | None = None
    after_state_anchor: str | None = None
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(ge=0)
    executor_version: str
    transport_adapter: str
    attempt_count: int = Field(ge=1, le=100)
    exit_state: Literal[
        "COMPLETED", "REJECTED", "BLOCKED", "FAILED", "INTERRUPTED",
        "DRIFTED", "TIMED_OUT", "CANCELLED", "RECOVERY_REQUIRED"
    ]
    verification_state: str
    artifact_hashes: tuple[str, ...] = ()
    stdout_hash_or_summary: str | None = None
    stderr_hash_or_summary: str | None = None
    checkpoint_ref: str | None = None
    blockers: tuple[str, ...] = ()
    policy_invariants: tuple[str, ...] = ()
    manual_terminal_interventions_per_task: Literal[0] = 0
    arbitrary_shell_exposed: Literal[False] = False
    main_merge: Literal[False] = False
    baseline_promotion: Literal[False] = False
    production_mutation: Literal[False] = False
    shared_db_mutation: Literal[False] = False


class AuthorityVerifier(Protocol):
    def verify(self, envelope: TaskEnvelopeV1, *, now: datetime) -> tuple[bool, tuple[str, ...]]: ...


class Ed25519AuthorityVerifierV1:
    def __init__(self, public_keys: Mapping[str, str]):
        self._keys: dict[str, Ed25519PublicKey] = {}
        for key_id, encoded in public_keys.items():
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) != 32:
                raise ValueError(f"ED25519_PUBLIC_KEY_LENGTH_INVALID:{key_id}")
            self._keys[key_id] = Ed25519PublicKey.from_public_bytes(raw)

    def verify(self, envelope: TaskEnvelopeV1, *, now: datetime) -> tuple[bool, tuple[str, ...]]:
        blockers: list[str] = []
        if envelope.execution_lease.revocation_state != "ACTIVE":
            blockers.append("LEASE_REVOKED")
        if now >= envelope.execution_lease.expires_at:
            blockers.append("LEASE_EXPIRED")
        if now >= envelope.expires_at:
            blockers.append("TASK_EXPIRED")
        if envelope.expected_remote_head.lower() != envelope.expected_base_sha.lower():
            blockers.append("EXPECTED_REMOTE_HEAD_DRIFT")
        key = self._keys.get(envelope.authority_proof.key_id)
        if key is None:
            blockers.append("AUTHORITY_KEY_UNKNOWN")
        else:
            try:
                signature = base64.b64decode(envelope.authority_proof.signature_b64, validate=True)
                key.verify(signature, envelope.canonical_bytes())
            except (ValueError, InvalidSignature):
                blockers.append("AUTHORITY_SIGNATURE_INVALID")
        return (not blockers, tuple(dict.fromkeys(blockers)))
