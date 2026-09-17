from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProviderId(str, Enum):
    NATIVE = "PALWAKF_NATIVE_AGENT"
    HERMES = "HERMES_AGENT"


class FilesystemPolicy(BaseModel):
    mode: Literal["READ_ONLY", "BOUNDED_WRITE"] = "READ_ONLY"
    allowed_roots: list[str] = Field(default_factory=list)
    allowed_patterns: list[str] = Field(default_factory=lambda: ["**"])


class NetworkPolicy(BaseModel):
    read: bool = False
    write: bool = False


class BoundedFileMutation(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2_000_000)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_before_sha256: str = Field(
        pattern=r"^(?:ABSENT|[0-9a-f]{64})$"
    )

    @model_validator(mode="after")
    def verify_content_hash(self):
        actual = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if actual != self.content_sha256:
            raise ValueError("BOUNDED_MUTATION_CONTENT_HASH_MISMATCH")
        return self


class ResourceBudget(BaseModel):
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    max_files: int = Field(default=500, ge=1, le=10000)
    max_bytes: int = Field(default=5_000_000, ge=1024, le=100_000_000)


class ExecutionEnvironment(BaseModel):
    project_id: str
    repository: str
    task_branch: str
    base_sha: str
    expected_head: str
    worktree: str
    filesystem_policy: FilesystemPolicy = Field(default_factory=FilesystemPolicy)
    network_policy: NetworkPolicy = Field(default_factory=NetworkPolicy)
    tool_policy: list[str] = Field(default_factory=list)
    secrets_policy: Literal["DENY"] = "DENY"
    db_authority: Literal["NONE", "READ_ONLY"] = "NONE"
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)

    @model_validator(mode="after")
    def fail_closed(self):
        if not self.task_branch.startswith("task/"):
            raise ValueError("TASK_BRANCH_REQUIRED")
        if self.network_policy.write:
            raise ValueError("NETWORK_WRITE_FORBIDDEN")
        return self


class AuthorizationEnvelope(BaseModel):
    authorization_id: str
    issuer: Literal["WORKSPACE_MANAGER", "HUMAN_EXPLICIT"]
    project_id: str
    task_id: str
    allowed_agent_ids: list[str]
    allowed_task_classes: list[str]
    allowed_provider_ids: list[ProviderId]
    allowed_model_providers: list[str] = Field(default_factory=lambda: ["none", "ollama"])
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_filesystem_roots: list[str] = Field(default_factory=list)
    allowed_path_patterns: list[str] = Field(default_factory=lambda: ["**"])
    read_only: bool = True
    allow_network_read: bool = False
    allow_network_write: bool = False
    agent_admission_reference: str | None = None

    @model_validator(mode="after")
    def fail_closed(self):
        if self.allow_network_write:
            raise ValueError("AUTHORITY_EXPANSION_NETWORK_WRITE_FORBIDDEN")
        return self


class UnifiedAgent(BaseModel):
    agent_id: str
    role_id: str
    runtime_profile_id: str
    skill_ids: list[str]
    tool_bindings: list[str]
    model_route: list[str]
    execution_provider_policy: list[ProviderId]
    memory_scopes: list[str]
    allowed_projects: list[str]
    permission_profile: str
    filesystem_scope: str
    network_scope: str
    data_limit: str
    evidence_requirement: str
    maturity: str
    authority_status: str
    source_commit_sha: str
    allowed_task_classes: list[str]
    runnable: bool
    required_admission_reference: str | None = None


class RunRequest(BaseModel):
    project_id: str
    task_id: str
    state_package_id: str
    agent_id: str
    role_id: str
    task_class: str
    objective: str
    provider_id: ProviderId = ProviderId.NATIVE
    provider_mode: str = "READ_ONLY_DIAGNOSTIC"
    model_provider: str = "none"
    model_id: str | None = None
    skill_ids: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    required_output_sentinel: str | None = None
    file_mutations: list[BoundedFileMutation] = Field(default_factory=list, max_length=64)
    authorization: AuthorizationEnvelope
    environment: ExecutionEnvironment


class RunReceipt(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run-{uuid4()}")
    project_id: str
    task_id: str
    state_package_id: str
    agent_id: str
    role_id: str
    skill_ids: list[str]
    provider_id: ProviderId
    provider_mode: str
    model_provider: str
    model_id: str | None
    tools: list[str]
    environment: dict[str, Any]
    base_sha: str
    before_head: str
    authorized_scope: dict[str, Any]
    plan: list[str]
    actions: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    changed_files: list[str]
    tests: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    retries: int
    evidence: list[dict[str, Any]]
    final_result: str
    next_action: str
    started_at: str = Field(default_factory=utc_now)
    finished_at: str = Field(default_factory=utc_now)
