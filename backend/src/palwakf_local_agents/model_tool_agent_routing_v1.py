from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderContractEnvelopeV1,
)


class ExecutionLeaseProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    compatibility_version: Literal["1"] = "1"
    contract_type: Literal["ExecutionLease"] = "ExecutionLease"
    project_id: str
    task_id: str
    correlation_id: str
    authority_scope: Literal["WORKSPACE_GOVERNED_EXECUTION"]
    producer: Literal["Workspace"]
    created_at: datetime
    provenance: tuple[str, ...]

    lease_id: str
    granted_scope: Literal["READ_ONLY_EXECUTION", "BOUNDED_SOURCE_WRITE"]
    expires_at: datetime
    allowed_capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    write_authority: Literal["NONE", "BOUNDED_SOURCE_WRITE"]
    revocation_state: Literal["ACTIVE", "REVOKED"]

    allowed_provider_ids: tuple[str, ...]
    allowed_agent_ids: tuple[str, ...]
    allowed_model_ids: tuple[str, ...]
    exact_base: str
    branch: str
    allowed_paths: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    approval_reference: str

    @model_validator(mode="after")
    def fail_closed(self) -> ExecutionLeaseProjectionV1:
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("LEASE_TIMESTAMPS_MUST_BE_TIMEZONE_AWARE")
        if self.expires_at <= self.created_at:
            raise ValueError("LEASE_EXPIRY_MUST_FOLLOW_CREATION")
        if self.granted_scope == "READ_ONLY_EXECUTION":
            if self.write_authority != "NONE" or self.allowed_paths:
                raise ValueError("READ_ONLY_LEASE_AUTHORITY_MISMATCH")
        elif self.write_authority != "BOUNDED_SOURCE_WRITE":
            raise ValueError("BOUNDED_WRITE_LEASE_AUTHORITY_MISMATCH")
        return self


class ModelDescriptorV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1, max_length=200)
    provider_id: Literal["ollama"]
    capabilities: tuple[str, ...] = Field(min_length=1, max_length=32)
    health: Literal["HEALTHY", "UNAVAILABLE"]
    admitted: bool
    local_only: Literal[True] = True
    evidence: tuple[str, ...] = Field(min_length=1, max_length=32)


class ToolDescriptorV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{1,119}$")
    provider_id: Literal["opencode", "playwright"]
    capability_id: str = Field(min_length=1, max_length=160)
    health: Literal["HEALTHY", "UNAVAILABLE"]
    admitted: bool
    mutation_class: Literal["READ_ONLY", "BOUNDED_SOURCE_WRITE"]
    evidence: tuple[str, ...] = Field(min_length=1, max_length=32)


class AgentDescriptorV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{1,119}$")
    role_id: str
    route_eligible: bool
    admission_basis: str
    capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    allowed_provider_ids: tuple[str, ...]
    allowed_model_providers: tuple[str, ...]
    mutation_ceiling: Literal["READ_ONLY", "BOUNDED_SOURCE_WRITE"]
    allowed_task_classes: tuple[str, ...]


class ExecutionRouteRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    task_id: str
    correlation_id: str
    branch: str
    current_head: str
    task_class: str
    agent_id: str
    required_capabilities: tuple[str, ...] = Field(min_length=1, max_length=32)
    required_tools: tuple[str, ...] = Field(default=(), max_length=32)
    model_required: bool = False
    requested_model_id: str | None = None
    mutation_class: Literal["READ_ONLY", "SOURCE_WRITE"] = "READ_ONLY"


class ExecutionRouteDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_allowed: bool
    blockers: tuple[str, ...]
    agent_id: str
    execution_provider_id: str | None
    model_provider_id: str | None
    model_id: str | None
    tool_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    capability_ids: tuple[str, ...]
    mutation_class: Literal["READ_ONLY", "SOURCE_WRITE"]
    lease_id: str
    no_authority_expansion: Literal[True] = True


def default_agent_descriptors_v1() -> tuple[AgentDescriptorV1, ...]:
    return (
        AgentDescriptorV1(
            agent_id="coordinator_agentic_v1",
            role_id="coordinator",
            route_eligible=False,
            admission_basis="REGISTRY_V2_ADMISSION_REQUIRED_MORE_RESTRICTIVE_WINS",
            capabilities=(
                "agent.headless_api",
                "model.inference",
                "model.health",
                "provider.health",
            ),
            allowed_tools=(),
            allowed_provider_ids=("hermes-headless", "ollama"),
            allowed_model_providers=("ollama",),
            mutation_ceiling="READ_ONLY",
            allowed_task_classes=("READ_ONLY_DIAGNOSTIC", "TASK_PLANNING"),
        ),
        AgentDescriptorV1(
            agent_id="sovereignty_reviewer_agentic_v1",
            role_id="sovereignty_reviewer",
            route_eligible=False,
            admission_basis="REGISTRY_V2_ADMISSION_REQUIRED_MORE_RESTRICTIVE_WINS",
            capabilities=(
                "agent.headless_api",
                "model.inference",
                "model.health",
                "provider.health",
            ),
            allowed_tools=(),
            allowed_provider_ids=("hermes-headless", "ollama"),
            allowed_model_providers=("ollama",),
            mutation_ceiling="READ_ONLY",
            allowed_task_classes=("READ_ONLY_DIAGNOSTIC", "POLICY_REVIEW"),
        ),
        AgentDescriptorV1(
            agent_id="coding_builder_agentic_v1",
            role_id="coding_builder",
            route_eligible=False,
            admission_basis="REGISTRY_V2_DISABLED_PENDING_ADMISSION",
            capabilities=(
                "engineering.analysis",
                "engineering.edit",
                "engineering.test",
            ),
            allowed_tools=("opencode.engineering_analysis",),
            allowed_provider_ids=("opencode",),
            allowed_model_providers=("ollama",),
            mutation_ceiling="READ_ONLY",
            allowed_task_classes=("REPOSITORY_ANALYSIS",),
        ),
        AgentDescriptorV1(
            agent_id="tester_agentic_v1",
            role_id="tester",
            route_eligible=False,
            admission_basis="REGISTRY_V2_DISABLED_PENDING_ADMISSION",
            capabilities=(
                "browser.uat",
                "browser.navigation",
                "browser.screenshot",
            ),
            allowed_tools=(
                "playwright.browser_uat",
                "playwright.browser_navigation",
                "playwright.browser_screenshot",
            ),
            allowed_provider_ids=("playwright",),
            allowed_model_providers=(),
            mutation_ceiling="READ_ONLY",
            allowed_task_classes=("TEST_TRIAGE",),
        ),
    )


def build_tool_descriptors_v1(
    providers: tuple[ProviderContractEnvelopeV1, ...],
    *,
    evidence_ref: str,
) -> tuple[ToolDescriptorV1, ...]:
    by_id = {item.provider_id: item for item in providers}
    out: list[ToolDescriptorV1] = []

    opencode = by_id.get("opencode")
    if opencode is not None:
        out.append(
            ToolDescriptorV1(
                tool_id="opencode.engineering_analysis",
                provider_id="opencode",
                capability_id="engineering.analysis",
                health=opencode.health,
                admitted=(
                    opencode.route_eligible
                    and "engineering.analysis" in opencode.admitted_capabilities
                ),
                mutation_class="READ_ONLY",
                evidence=(evidence_ref,),
            )
        )

    playwright = by_id.get("playwright")
    if playwright is not None:
        for suffix, capability in (
            ("browser_uat", "browser.uat"),
            ("browser_navigation", "browser.navigation"),
            ("browser_screenshot", "browser.screenshot"),
        ):
            out.append(
                ToolDescriptorV1(
                    tool_id=f"playwright.{suffix}",
                    provider_id="playwright",
                    capability_id=capability,
                    health=playwright.health,
                    admitted=(
                        playwright.route_eligible
                        and capability in playwright.admitted_capabilities
                    ),
                    mutation_class="READ_ONLY",
                    evidence=(evidence_ref,),
                )
            )

    return tuple(out)


def _provider_by_id(
    providers: tuple[ProviderContractEnvelopeV1, ...],
) -> dict[str, ProviderContractEnvelopeV1]:
    return {item.provider_id: item for item in providers}


def _provider_supports(
    provider: ProviderContractEnvelopeV1 | None,
    capability: str,
) -> bool:
    return bool(
        provider
        and provider.lifecycle == "ADMITTED"
        and provider.health == "HEALTHY"
        and provider.route_eligible
        and capability in provider.admitted_capabilities
    )


def route_execution_v1(
    request: ExecutionRouteRequestV1,
    *,
    lease: ExecutionLeaseProjectionV1,
    providers: tuple[ProviderContractEnvelopeV1, ...],
    models: tuple[ModelDescriptorV1, ...],
    tools: tuple[ToolDescriptorV1, ...],
    agents: tuple[AgentDescriptorV1, ...] | None = None,
    now: datetime | None = None,
) -> ExecutionRouteDecisionV1:
    observed = now or datetime.now(UTC)
    blockers: list[str] = []
    agent_map = {
        item.agent_id: item
        for item in (agents or default_agent_descriptors_v1())
    }
    provider_map = _provider_by_id(providers)
    model_map = {item.model_id: item for item in models}
    tool_map = {item.tool_id: item for item in tools}

    if lease.revocation_state != "ACTIVE":
        blockers.append("LEASE_REVOKED")
    if observed >= lease.expires_at:
        blockers.append("LEASE_EXPIRED")
    if request.project_id != lease.project_id:
        blockers.append("LEASE_PROJECT_MISMATCH")
    if request.task_id != lease.task_id:
        blockers.append("LEASE_TASK_MISMATCH")
    if request.correlation_id != lease.correlation_id:
        blockers.append("LEASE_CORRELATION_MISMATCH")
    if request.branch != lease.branch:
        blockers.append("LEASE_BRANCH_MISMATCH")
    if request.current_head.lower() != lease.exact_base.lower():
        blockers.append("LEASE_EXACT_BASE_MISMATCH")

    if any(
        capability not in lease.allowed_capabilities
        for capability in request.required_capabilities
    ):
        blockers.append("LEASE_CAPABILITY_NOT_ALLOWED")
    if any(tool not in lease.allowed_tools for tool in request.required_tools):
        blockers.append("LEASE_TOOL_NOT_ALLOWED")
    if request.agent_id not in lease.allowed_agent_ids:
        blockers.append("LEASE_AGENT_NOT_ALLOWED")
    if (
        request.mutation_class == "SOURCE_WRITE"
        and lease.write_authority != "BOUNDED_SOURCE_WRITE"
    ):
        blockers.append("LEASE_WRITE_AUTHORITY_REQUIRED")

    agent = agent_map.get(request.agent_id)
    if agent is None:
        blockers.append("AGENT_UNKNOWN")
    else:
        if not agent.route_eligible:
            blockers.append("AGENT_NOT_ADMITTED")
        if request.task_class not in agent.allowed_task_classes:
            blockers.append("AGENT_TASK_CLASS_NOT_ALLOWED")
        if any(
            capability not in agent.capabilities
            for capability in request.required_capabilities
        ):
            blockers.append("AGENT_CAPABILITY_NOT_ALLOWED")
        if any(tool not in agent.allowed_tools for tool in request.required_tools):
            blockers.append("AGENT_TOOL_NOT_ALLOWED")
        if (
            request.mutation_class == "SOURCE_WRITE"
            and agent.mutation_ceiling != "BOUNDED_SOURCE_WRITE"
        ):
            blockers.append("AGENT_MUTATION_CEILING_EXCEEDED")

    selected_execution_provider: str | None = None
    if "agent.headless_api" in request.required_capabilities:
        hermes = provider_map.get("hermes-headless")
        if (
            "hermes-headless" not in lease.allowed_provider_ids
            or agent is None
            or "hermes-headless" not in agent.allowed_provider_ids
            or not _provider_supports(hermes, "agent.headless_api")
        ):
            blockers.append("HERMES_HEADLESS_ROUTE_NOT_ALLOWED")
        else:
            selected_execution_provider = "hermes-headless"

    selected_model: str | None = None
    model_provider_id: str | None = None
    if request.model_required:
        candidate_id = request.requested_model_id
        if candidate_id is None:
            candidates = [
                item
                for item in models
                if item.admitted
                and item.health == "HEALTHY"
                and item.model_id in lease.allowed_model_ids
            ]
            candidate_id = candidates[0].model_id if candidates else None

        model = model_map.get(candidate_id or "")
        ollama = provider_map.get("ollama")
        if model is None:
            blockers.append("MODEL_NOT_AVAILABLE")
        else:
            if model.model_id not in lease.allowed_model_ids:
                blockers.append("LEASE_MODEL_NOT_ALLOWED")
            if (
                "ollama" not in lease.allowed_provider_ids
                or agent is None
                or "ollama" not in agent.allowed_provider_ids
                or "ollama" not in agent.allowed_model_providers
                or not _provider_supports(ollama, "model.inference")
                or not model.admitted
                or model.health != "HEALTHY"
                or "model.inference" not in model.capabilities
            ):
                blockers.append("MODEL_ROUTE_NOT_ALLOWED")
            else:
                selected_model = model.model_id
                model_provider_id = "ollama"

    selected_tools: list[str] = []
    selected_provider_ids: list[str] = []
    if selected_execution_provider:
        selected_provider_ids.append(selected_execution_provider)
    if model_provider_id and model_provider_id not in selected_provider_ids:
        selected_provider_ids.append(model_provider_id)

    for tool_id in request.required_tools:
        tool = tool_map.get(tool_id)
        if tool is None:
            blockers.append(f"TOOL_UNKNOWN:{tool_id}")
            continue
        provider = provider_map.get(tool.provider_id)
        if not tool.admitted or tool.health != "HEALTHY":
            blockers.append(f"TOOL_NOT_ADMITTED:{tool_id}")
            continue
        if tool.provider_id not in lease.allowed_provider_ids:
            blockers.append(f"LEASE_TOOL_PROVIDER_NOT_ALLOWED:{tool_id}")
            continue
        if not _provider_supports(provider, tool.capability_id):
            blockers.append(f"TOOL_PROVIDER_CAPABILITY_NOT_ADMITTED:{tool_id}")
            continue
        if (
            request.mutation_class == "SOURCE_WRITE"
            and tool.mutation_class != "BOUNDED_SOURCE_WRITE"
        ):
            blockers.append(f"TOOL_WRITE_AUTHORITY_NOT_ADMITTED:{tool_id}")
            continue
        selected_tools.append(tool_id)
        if tool.provider_id not in selected_provider_ids:
            selected_provider_ids.append(tool.provider_id)

    return ExecutionRouteDecisionV1(
        dispatch_allowed=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
        agent_id=request.agent_id,
        execution_provider_id=selected_execution_provider,
        model_provider_id=model_provider_id,
        model_id=selected_model,
        tool_ids=tuple(selected_tools),
        provider_ids=tuple(selected_provider_ids),
        capability_ids=request.required_capabilities,
        mutation_class=request.mutation_class,
        lease_id=lease.lease_id,
    )
