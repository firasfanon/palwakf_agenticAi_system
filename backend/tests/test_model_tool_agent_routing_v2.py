from datetime import UTC, datetime, timedelta

from palwakf_local_agents.model_tool_agent_routing_v1 import ExecutionLeaseProjectionV1
from palwakf_local_agents.model_tool_agent_routing_v2 import (
    RemoteTransportRouteRequestV2,
    build_remote_transport_tools_v2,
    route_remote_transport_v2,
)
from palwakf_local_agents.provider_runtime_registry_v2 import (
    REMOTE_CAPABILITY_IDS_V2,
    ProviderRuntimeRegistryV2,
)


HEAD = "73cca89c8928cdc688d271bb5a92053e1f785414"
BRANCH = "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1"


def provider():
    registry = ProviderRuntimeRegistryV2()
    registry.record_probe(
        healthy=True,
        version="bootstrap-proven",
        endpoint="mcp://palwakf-remote",
        evidence_ref="evidence://probe",
    )
    registry.record_benchmark(success=True, evidence_ref="evidence://benchmark")
    registry.admit(
        evidence_ref="evidence://admission",
        admitted_capabilities=REMOTE_CAPABILITY_IDS_V2,
    )
    return registry.contract_envelope(
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        task_id="AUTONOMOUS-EXECUTION-CHANNEL-BINDING-V1",
        correlation_id="autonomous-execution-channel-binding-v1",
        provenance=("test",),
        created_at=datetime.now(UTC),
    )


def lease(capability="mesh_hostname", tool=None, write=False):
    now = datetime.now(UTC)
    tool_id = tool or f"palwakf-remote-mcp.{capability}"
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": "AUTONOMOUS-EXECUTION-CHANNEL-BINDING-V1",
        "correlation_id": "autonomous-execution-channel-binding-v1",
        "created_at": now,
        "provenance": ("test",),
        "lease_id": "lease-autonomous-channel-binding-v2",
        "granted_scope": "READ_ONLY_EXECUTION",
        "expires_at": now + timedelta(minutes=20),
        "allowed_capabilities": (capability,),
        "allowed_tools": (tool_id,),
        "write_authority": "NONE",
        "revocation_state": "ACTIVE",
        "allowed_provider_ids": ("palwakf-remote-mcp",),
        "allowed_agent_ids": ("coordinator_agentic_v1",),
        "allowed_model_ids": (),
        "exact_base": HEAD,
        "branch": BRANCH,
        "allowed_paths": (),
        "forbidden_operations": (
            "source_write",
            "arbitrary_shell",
            "main_merge",
            "baseline_promotion",
            "production",
            "shared_db_mutation",
        ),
        "approval_reference": "AUTH://AUTONOMOUS_EXECUTION_CHANNEL_BINDING_V1",
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    if write:
        data.update(
            {
                "granted_scope": "BOUNDED_SOURCE_WRITE",
                "write_authority": "BOUNDED_SOURCE_WRITE",
                "allowed_paths": ("backend/src/**",),
            }
        )
    return ExecutionLeaseProjectionV1.model_validate(data)


def request(capability="mesh_hostname", mutation="READ_ONLY", tool=None):
    return RemoteTransportRouteRequestV2(
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        task_id="AUTONOMOUS-EXECUTION-CHANNEL-BINDING-V1",
        correlation_id="autonomous-execution-channel-binding-v1",
        branch=BRANCH,
        current_head=HEAD,
        agent_id="coordinator_agentic_v1",
        capability_id=capability,
        tool_id=tool or f"palwakf-remote-mcp.{capability}",
        mutation_class=mutation,
    )


def test_exact_remote_route_is_allowed() -> None:
    p = provider()
    tools = build_remote_transport_tools_v2(p, evidence_ref="evidence://tools")
    decision = route_remote_transport_v2(
        request(),
        lease=lease(),
        provider=p,
        tools=tools,
    )
    assert decision.dispatch_allowed is True
    assert decision.blockers == ()
    assert decision.provider_id == "palwakf-remote-mcp"
    assert decision.transport_only is True
    assert decision.no_sovereign_authority is True
    assert decision.no_authority_expansion is True


def test_missing_provider_in_lease_is_blocked() -> None:
    p = provider()
    tools = build_remote_transport_tools_v2(p, evidence_ref="evidence://tools")
    bad_lease = lease().model_copy(update={"allowed_provider_ids": ("ollama",)})
    decision = route_remote_transport_v2(
        request(),
        lease=bad_lease,
        provider=p,
        tools=tools,
    )
    assert decision.dispatch_allowed is False
    assert "LEASE_REMOTE_PROVIDER_NOT_ALLOWED" in decision.blockers


def test_source_write_authority_is_blocked_in_p2() -> None:
    p = provider()
    tools = build_remote_transport_tools_v2(p, evidence_ref="evidence://tools")
    decision = route_remote_transport_v2(
        request(),
        lease=lease(write=True),
        provider=p,
        tools=tools,
    )
    assert decision.dispatch_allowed is False
    assert "P2_SOURCE_WRITE_AUTHORITY_FORBIDDEN" in decision.blockers
    assert "P2_LEASE_SCOPE_MUST_REMAIN_READ_ONLY_EXECUTION" in decision.blockers


def test_mutation_class_must_match_capability() -> None:
    p = provider()
    tools = build_remote_transport_tools_v2(p, evidence_ref="evidence://tools")
    active = lease("temp_write")
    decision = route_remote_transport_v2(
        request("temp_write", mutation="READ_ONLY"),
        lease=active,
        provider=p,
        tools=tools,
    )
    assert decision.dispatch_allowed is False
    assert "REMOTE_MUTATION_CLASS_MISMATCH" in decision.blockers


def test_wrong_tool_is_blocked() -> None:
    p = provider()
    tools = build_remote_transport_tools_v2(p, evidence_ref="evidence://tools")
    decision = route_remote_transport_v2(
        request(tool="palwakf-remote-mcp.git_readback"),
        lease=lease(),
        provider=p,
        tools=tools,
    )
    assert decision.dispatch_allowed is False
    assert "REMOTE_TOOL_CAPABILITY_MISMATCH" in decision.blockers
    assert "LEASE_REMOTE_TOOL_NOT_ALLOWED" in decision.blockers
