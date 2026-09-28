from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.model_tool_agent_routing_v1 import ExecutionLeaseProjectionV1
from palwakf_local_agents.provider_runtime_registry_v2 import (
    REMOTE_CAPABILITY_IDS_V2,
    RemoteTransportProviderEnvelopeV2,
)


_MUTATION_CLASS_BY_CAPABILITY: dict[str, str] = {
    "mesh_device_info": "READ_ONLY",
    "mesh_hostname": "READ_ONLY",
    "file_read": "READ_ONLY",
    "temp_write": "BOUNDED_TEMP_MUTATION",
    "temp_delete": "BOUNDED_TEMP_MUTATION",
    "bounded_powershell": "BOUNDED_COMMAND",
    "process_port_readback": "READ_ONLY",
    "git_readback": "READ_ONLY",
    "playwright_screenshot_uat": "BROWSER_UAT",
    "audit_readback": "READ_ONLY",
}


class RemoteTransportToolDescriptorV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str = Field(pattern=r"^palwakf-remote-mcp\.[a-z0-9_.-]{2,80}$")
    provider_id: Literal["palwakf-remote-mcp"] = "palwakf-remote-mcp"
    capability_id: str
    mutation_class: Literal[
        "READ_ONLY", "BOUNDED_TEMP_MUTATION", "BOUNDED_COMMAND", "BROWSER_UAT"
    ]
    health: Literal["HEALTHY"]
    admitted: bool
    evidence: tuple[str, ...] = Field(min_length=1, max_length=32)


def build_remote_transport_tools_v2(
    provider: RemoteTransportProviderEnvelopeV2,
    *,
    evidence_ref: str,
) -> tuple[RemoteTransportToolDescriptorV2, ...]:
    out: list[RemoteTransportToolDescriptorV2] = []
    for capability in REMOTE_CAPABILITY_IDS_V2:
        out.append(
            RemoteTransportToolDescriptorV2(
                tool_id=f"palwakf-remote-mcp.{capability}",
                capability_id=capability,
                mutation_class=_MUTATION_CLASS_BY_CAPABILITY[capability],
                health="HEALTHY",
                admitted=(
                    provider.route_eligible
                    and provider.health == "HEALTHY"
                    and capability in provider.admitted_capabilities
                ),
                evidence=(evidence_ref,),
            )
        )
    return tuple(out)


class RemoteTransportRouteRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    task_id: str
    correlation_id: str
    branch: str
    current_head: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    agent_id: str
    capability_id: str
    tool_id: str
    mutation_class: Literal[
        "READ_ONLY", "BOUNDED_TEMP_MUTATION", "BOUNDED_COMMAND", "BROWSER_UAT"
    ]


class RemoteTransportRouteDecisionV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dispatch_allowed: bool
    blockers: tuple[str, ...]
    provider_id: Literal["palwakf-remote-mcp"] = "palwakf-remote-mcp"
    capability_id: str
    tool_id: str
    mutation_class: str
    lease_id: str
    transport_only: Literal[True] = True
    no_sovereign_authority: Literal[True] = True
    no_authority_expansion: Literal[True] = True


def route_remote_transport_v2(
    request: RemoteTransportRouteRequestV2,
    *,
    lease: ExecutionLeaseProjectionV1,
    provider: RemoteTransportProviderEnvelopeV2,
    tools: tuple[RemoteTransportToolDescriptorV2, ...],
    now: datetime | None = None,
) -> RemoteTransportRouteDecisionV2:
    observed = now or datetime.now(UTC)
    blockers: list[str] = []
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
    if request.agent_id not in lease.allowed_agent_ids:
        blockers.append("LEASE_AGENT_NOT_ALLOWED")
    if "palwakf-remote-mcp" not in lease.allowed_provider_ids:
        blockers.append("LEASE_REMOTE_PROVIDER_NOT_ALLOWED")
    if request.capability_id not in lease.allowed_capabilities:
        blockers.append("LEASE_REMOTE_CAPABILITY_NOT_ALLOWED")
    if request.tool_id not in lease.allowed_tools:
        blockers.append("LEASE_REMOTE_TOOL_NOT_ALLOWED")

    if lease.write_authority != "NONE":
        blockers.append("P2_SOURCE_WRITE_AUTHORITY_FORBIDDEN")
    if lease.granted_scope != "READ_ONLY_EXECUTION":
        blockers.append("P2_LEASE_SCOPE_MUST_REMAIN_READ_ONLY_EXECUTION")

    if not provider.route_eligible or provider.health != "HEALTHY":
        blockers.append("REMOTE_TRANSPORT_PROVIDER_NOT_ADMITTED")
    if request.capability_id not in provider.admitted_capabilities:
        blockers.append("REMOTE_TRANSPORT_CAPABILITY_NOT_ADMITTED")

    expected_tool_id = f"palwakf-remote-mcp.{request.capability_id}"
    if request.tool_id != expected_tool_id:
        blockers.append("REMOTE_TOOL_CAPABILITY_MISMATCH")

    tool = tool_map.get(request.tool_id)
    if tool is None:
        blockers.append("REMOTE_TOOL_UNKNOWN")
    else:
        if not tool.admitted or tool.health != "HEALTHY":
            blockers.append("REMOTE_TOOL_NOT_ADMITTED")
        if tool.capability_id != request.capability_id:
            blockers.append("REMOTE_TOOL_CAPABILITY_MISMATCH")
        expected_mutation = _MUTATION_CLASS_BY_CAPABILITY.get(request.capability_id)
        if expected_mutation is None:
            blockers.append("REMOTE_CAPABILITY_UNKNOWN")
        elif request.mutation_class != expected_mutation:
            blockers.append("REMOTE_MUTATION_CLASS_MISMATCH")
        if tool.mutation_class != request.mutation_class:
            blockers.append("REMOTE_TOOL_MUTATION_CLASS_MISMATCH")

    unique = tuple(dict.fromkeys(blockers))
    return RemoteTransportRouteDecisionV2(
        dispatch_allowed=not unique,
        blockers=unique,
        capability_id=request.capability_id,
        tool_id=request.tool_id,
        mutation_class=request.mutation_class,
        lease_id=lease.lease_id,
    )
