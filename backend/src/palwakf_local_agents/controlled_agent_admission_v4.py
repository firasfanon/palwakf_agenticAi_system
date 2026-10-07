from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from palwakf_local_agents.model_tool_agent_routing_v1 import (
    AgentDescriptorV1,
    ExecutionLeaseProjectionV1,
    default_agent_descriptors_v1,
)

VISUAL_QA_AGENT_ID = "tester_agentic_v1"
VISUAL_QA_CAPABILITIES = (
    "browser.uat",
    "browser.navigation",
    "browser.screenshot",
)
VISUAL_QA_TOOLS = (
    "playwright.browser_uat",
    "playwright.browser_navigation",
    "playwright.browser_screenshot",
)
VISUAL_QA_PROVIDER_IDS = ("playwright",)
VISUAL_QA_RUNTIME_TASK_CLASSES = ("TEST_TRIAGE",)
VISUAL_QA_OUTPUTS = ("visual_qa_report",)

ControlledAgentIdV4 = Literal[
    "coordinator_agentic_v1",
    "sovereignty_reviewer_agentic_v1",
    "knowledge_researcher_agentic_v1",
    "tester_agentic_v1",
]


class ControlledAgentAdmissionReceiptV4(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    schema_name: Literal["palwakf.controlled_agent_admission.v4"] = Field(
        default="palwakf.controlled_agent_admission.v4",
        alias="schema",
        serialization_alias="schema",
    )
    admission_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{5,159}$")
    agent_id: ControlledAgentIdV4
    admission_status: Literal["ADMITTED"] = "ADMITTED"
    admission_scope: Literal["READ_ONLY_EXECUTION"] = "READ_ONLY_EXECUTION"
    created_at: datetime
    expires_at: datetime
    human_authority_reference: str = Field(min_length=12, max_length=500)
    self_authorized: Literal[False] = False

    lease_id: str
    exact_base: str
    branch: str
    allowed_capabilities: tuple[str, ...] = Field(min_length=1, max_length=32)
    allowed_provider_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    allowed_model_ids: tuple[str, ...] = Field(default=(), max_length=16)
    allowed_tools: tuple[str, ...] = Field(default=(), max_length=16)
    allowed_task_classes: tuple[str, ...] = Field(min_length=1, max_length=16)
    allowed_outputs: tuple[str, ...] = Field(min_length=1, max_length=16)

    mutation_ceiling: Literal["READ_ONLY"] = "READ_ONLY"
    write_authority: Literal["NONE"] = "NONE"
    source_write_allowed: Literal[False] = False
    opencode_source_write_allowed: Literal[False] = False
    playwright_admission_allowed: bool = False
    hermes_bounded_write_allowed: Literal[False] = False
    delegation_allowed: Literal[False] = False
    parallel_multi_agent_allowed: Literal[False] = False
    production_authority: Literal[False] = False
    shared_db_mutation_authority: Literal[False] = False

    evidence: tuple[str, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def fail_closed(self) -> ControlledAgentAdmissionReceiptV4:
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("AGENT_ADMISSION_TIMESTAMPS_MUST_BE_TIMEZONE_AWARE")
        if self.expires_at <= self.created_at:
            raise ValueError("AGENT_ADMISSION_EXPIRY_MUST_FOLLOW_CREATION")
        for values, error in (
            (self.allowed_capabilities, "DUPLICATE_AGENT_ADMISSION_CAPABILITY"),
            (self.allowed_provider_ids, "DUPLICATE_AGENT_ADMISSION_PROVIDER"),
            (self.allowed_model_ids, "DUPLICATE_AGENT_ADMISSION_MODEL"),
            (self.allowed_tools, "DUPLICATE_AGENT_ADMISSION_TOOL"),
            (self.allowed_task_classes, "DUPLICATE_AGENT_ADMISSION_TASK_CLASS"),
            (self.allowed_outputs, "DUPLICATE_AGENT_ADMISSION_OUTPUT"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(error)

        if self.agent_id == VISUAL_QA_AGENT_ID:
            if not self.playwright_admission_allowed:
                raise ValueError("VISUAL_QA_PLAYWRIGHT_ADMISSION_REQUIRED")
            if self.allowed_capabilities != VISUAL_QA_CAPABILITIES:
                raise ValueError("VISUAL_QA_CAPABILITY_SCOPE_MISMATCH")
            if self.allowed_tools != VISUAL_QA_TOOLS:
                raise ValueError("VISUAL_QA_PLAYWRIGHT_TOOL_SCOPE_MISMATCH")
            if self.allowed_provider_ids != VISUAL_QA_PROVIDER_IDS:
                raise ValueError("VISUAL_QA_PROVIDER_SCOPE_MISMATCH")
            if self.allowed_model_ids:
                raise ValueError("VISUAL_QA_MODEL_SCOPE_MUST_BE_EMPTY")
            if self.allowed_task_classes != VISUAL_QA_RUNTIME_TASK_CLASSES:
                raise ValueError("VISUAL_QA_RUNTIME_TASK_CLASS_MISMATCH")
            if self.allowed_outputs != VISUAL_QA_OUTPUTS:
                raise ValueError("VISUAL_QA_OUTPUT_SCOPE_MISMATCH")
        else:
            if self.playwright_admission_allowed:
                raise ValueError("PLAYWRIGHT_ADMISSION_ONLY_FOR_VISUAL_QA")
            if self.allowed_tools:
                raise ValueError("NON_VISUAL_READ_ONLY_AGENT_V4_MUST_NOT_ADMIT_TOOLS")
        return self


def apply_controlled_agent_admission_v4(
    receipt: ControlledAgentAdmissionReceiptV4,
    *,
    lease: ExecutionLeaseProjectionV1,
    agents: tuple[AgentDescriptorV1, ...] | None = None,
    now: datetime | None = None,
) -> tuple[AgentDescriptorV1, ...]:
    observed = now or datetime.now(UTC)
    descriptors = agents or default_agent_descriptors_v1()

    if lease.revocation_state != "ACTIVE":
        raise ValueError("AGENT_ADMISSION_REQUIRES_ACTIVE_LEASE")
    if observed >= lease.expires_at:
        raise ValueError("AGENT_ADMISSION_LEASE_EXPIRED")
    if observed >= receipt.expires_at:
        raise ValueError("AGENT_ADMISSION_EXPIRED")
    if receipt.created_at < lease.created_at:
        raise ValueError("AGENT_ADMISSION_PREDATES_LEASE")
    if receipt.expires_at > lease.expires_at:
        raise ValueError("AGENT_ADMISSION_MUST_NOT_OUTLIVE_LEASE")
    if lease.granted_scope != "READ_ONLY_EXECUTION":
        raise ValueError("AGENT_ADMISSION_REQUIRES_READ_ONLY_LEASE")
    if lease.write_authority != "NONE":
        raise ValueError("AGENT_ADMISSION_REQUIRES_NO_WRITE_AUTHORITY")
    if lease.allowed_paths:
        raise ValueError("AGENT_ADMISSION_READ_ONLY_LEASE_PATHS_MUST_BE_EMPTY")

    if receipt.lease_id != lease.lease_id:
        raise ValueError("AGENT_ADMISSION_LEASE_ID_MISMATCH")
    if receipt.human_authority_reference != lease.approval_reference:
        raise ValueError("AGENT_ADMISSION_HUMAN_AUTHORITY_MISMATCH")
    if receipt.exact_base.lower() != lease.exact_base.lower():
        raise ValueError("AGENT_ADMISSION_EXACT_BASE_MISMATCH")
    if receipt.branch != lease.branch:
        raise ValueError("AGENT_ADMISSION_BRANCH_MISMATCH")
    if receipt.agent_id not in lease.allowed_agent_ids:
        raise ValueError("AGENT_NOT_ALLOWED_BY_LEASE")

    if any(
        capability not in lease.allowed_capabilities
        for capability in receipt.allowed_capabilities
    ):
        raise ValueError("AGENT_ADMISSION_CAPABILITY_EXCEEDS_LEASE")
    if any(
        provider_id not in lease.allowed_provider_ids
        for provider_id in receipt.allowed_provider_ids
    ):
        raise ValueError("AGENT_ADMISSION_PROVIDER_EXCEEDS_LEASE")
    if any(
        model_id not in lease.allowed_model_ids
        for model_id in receipt.allowed_model_ids
    ):
        raise ValueError("AGENT_ADMISSION_MODEL_EXCEEDS_LEASE")
    if receipt.allowed_tools != lease.allowed_tools:
        raise ValueError("AGENT_ADMISSION_TOOL_SCOPE_MISMATCH")

    by_id = {item.agent_id: item for item in descriptors}
    target = by_id.get(receipt.agent_id)
    if target is None:
        raise ValueError("AGENT_ADMISSION_TARGET_UNKNOWN")
    if target.mutation_ceiling != "READ_ONLY":
        raise ValueError("AGENT_ADMISSION_TARGET_NOT_READ_ONLY")
    if any(
        capability not in target.capabilities
        for capability in receipt.allowed_capabilities
    ):
        raise ValueError("AGENT_ADMISSION_CAPABILITY_NOT_DECLARED")
    if any(
        provider_id not in target.allowed_provider_ids
        for provider_id in receipt.allowed_provider_ids
    ):
        raise ValueError("AGENT_ADMISSION_PROVIDER_NOT_DECLARED")
    if any(tool not in target.allowed_tools for tool in receipt.allowed_tools):
        raise ValueError("AGENT_ADMISSION_TOOL_NOT_DECLARED")
    if any(
        task_class not in target.allowed_task_classes
        for task_class in receipt.allowed_task_classes
    ):
        raise ValueError("AGENT_ADMISSION_TASK_CLASS_NOT_DECLARED")

    admitted = target.model_copy(
        update={
            "route_eligible": True,
            "admission_basis": (
                f"HUMAN_AUTHORIZED_FRESH_WORKSPACE_LEASE_V4:{receipt.admission_id}"
            ),
            "capabilities": receipt.allowed_capabilities,
            "allowed_tools": receipt.allowed_tools,
            "allowed_provider_ids": receipt.allowed_provider_ids,
            "allowed_task_classes": receipt.allowed_task_classes,
            "mutation_ceiling": "READ_ONLY",
        }
    )

    return tuple(
        admitted if item.agent_id == receipt.agent_id else item for item in descriptors
    )
