from datetime import UTC, datetime, timedelta

from palwakf_local_agents.model_tool_agent_routing_v1 import (
    ExecutionLeaseProjectionV1,
    ExecutionRouteRequestV1,
    ModelDescriptorV1,
    build_tool_descriptors_v1,
    default_agent_descriptors_v1,
    route_execution_v1,
)
from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderRuntimeRegistryV1,
)

NOW = datetime(2026, 9, 27, 21, 0, tzinfo=UTC)


def admitted_providers():
    registry = ProviderRuntimeRegistryV1()

    registry.record_probe(
        "hermes-headless",
        healthy=True,
        version="0.21.4",
        evidence_ref="hermes:probe",
    )
    registry.record_benchmark(
        "hermes-headless",
        success=True,
        evidence_ref="hermes:benchmark",
    )
    registry.admit(
        "hermes-headless",
        evidence_ref="hermes:admission",
        admitted_capabilities=("agent.headless_api", "provider.health"),
    )

    registry.record_probe(
        "ollama",
        healthy=True,
        version="0.34.3",
        evidence_ref="ollama:probe",
    )
    registry.record_benchmark(
        "ollama",
        success=True,
        evidence_ref="ollama:benchmark",
    )
    registry.admit(
        "ollama",
        evidence_ref="ollama:admission",
        admitted_capabilities=(
            "model.inference",
            "model.health",
            "model.list",
        ),
    )

    registry.record_probe(
        "opencode",
        healthy=True,
        version="2.0.18",
        evidence_ref="opencode:probe",
    )
    registry.record_benchmark(
        "opencode",
        success=True,
        evidence_ref="opencode:benchmark",
    )
    registry.admit(
        "opencode",
        evidence_ref="opencode:admission",
        admitted_capabilities=("engineering.analysis", "provider.health"),
    )

    registry.record_probe(
        "playwright",
        healthy=True,
        version="1.63.0",
        evidence_ref="playwright:probe",
    )
    registry.record_benchmark(
        "playwright",
        success=True,
        evidence_ref="playwright:benchmark",
    )
    registry.admit(
        "playwright",
        evidence_ref="playwright:admission",
        admitted_capabilities=(
            "browser.uat",
            "browser.navigation",
            "browser.screenshot",
            "provider.health",
        ),
    )

    return tuple(
        registry.contract_envelope(
            provider_id,
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="MODEL-TOOL-AGENT-ROUTING-V1",
            correlation_id="routing-v1",
            provenance=("routing-test",),
            created_at=NOW,
        )
        for provider_id in (
            "hermes-headless",
            "ollama",
            "opencode",
            "playwright",
        )
    )


def lease(**updates) -> ExecutionLeaseProjectionV1:
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": "MODEL-TOOL-AGENT-ROUTING-V1",
        "correlation_id": "routing-v1",
        "created_at": NOW,
        "provenance": ("workspace-lease",),
        "lease_id": "lease-routing-v1",
        "granted_scope": "READ_ONLY_EXECUTION",
        "expires_at": NOW + timedelta(hours=1),
        "allowed_capabilities": (
            "agent.headless_api",
            "model.inference",
            "model.health",
            "provider.health",
        ),
        "allowed_tools": (),
        "write_authority": "NONE",
        "revocation_state": "ACTIVE",
        "allowed_provider_ids": ("hermes-headless", "ollama"),
        "allowed_agent_ids": ("coordinator_agentic_v1",),
        "allowed_model_ids": ("qwen2.5:3b",),
        "exact_base": "40d28da2953b1aceed466388d217d6b88533becb",
        "branch": "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
        "allowed_paths": (),
        "forbidden_operations": ("production", "shared_db_mutation"),
        "approval_reference": "WORKSPACE://routing-v1",
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    data.update(updates)
    return ExecutionLeaseProjectionV1.model_validate(data)


def models():
    return (
        ModelDescriptorV1(
            model_id="qwen2.5:3b",
            provider_id="ollama",
            capabilities=("model.inference",),
            health="HEALTHY",
            admitted=True,
            evidence=("ollama:benchmark",),
        ),
    )


def test_coordinator_route_is_blocked_by_current_v2_agent_admission() -> None:
    providers = admitted_providers()
    decision = route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="MODEL-TOOL-AGENT-ROUTING-V1",
            correlation_id="routing-v1",
            branch="task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
            current_head="40d28da2953b1aceed466388d217d6b88533becb",
            task_class="READ_ONLY_DIAGNOSTIC",
            agent_id="coordinator_agentic_v1",
            required_capabilities=("agent.headless_api", "model.inference"),
            model_required=True,
            requested_model_id="qwen2.5:3b",
        ),
        lease=lease(),
        providers=providers,
        models=models(),
        tools=build_tool_descriptors_v1(
            providers,
            evidence_ref="routing-test",
        ),
        now=NOW,
    )

    assert decision.dispatch_allowed is False
    assert "AGENT_NOT_ADMITTED" in decision.blockers
    assert decision.execution_provider_id == "hermes-headless"
    assert decision.model_provider_id == "ollama"
    assert decision.model_id == "qwen2.5:3b"


def test_coding_builder_is_blocked_even_when_opencode_provider_is_admitted() -> None:
    providers = admitted_providers()
    decision = route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="MODEL-TOOL-AGENT-ROUTING-V1",
            correlation_id="routing-v1",
            branch="task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
            current_head="40d28da2953b1aceed466388d217d6b88533becb",
            task_class="REPOSITORY_ANALYSIS",
            agent_id="coding_builder_agentic_v1",
            required_capabilities=("engineering.analysis",),
            required_tools=("opencode.engineering_analysis",),
        ),
        lease=lease(
            allowed_capabilities=("engineering.analysis",),
            allowed_tools=("opencode.engineering_analysis",),
            allowed_provider_ids=("opencode",),
            allowed_agent_ids=("coding_builder_agentic_v1",),
            allowed_model_ids=(),
        ),
        providers=providers,
        models=(),
        tools=build_tool_descriptors_v1(
            providers,
            evidence_ref="routing-test",
        ),
        now=NOW,
    )

    assert decision.dispatch_allowed is False
    assert "AGENT_NOT_ADMITTED" in decision.blockers


def test_tester_is_blocked_even_when_playwright_provider_is_admitted() -> None:
    providers = admitted_providers()
    decision = route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="MODEL-TOOL-AGENT-ROUTING-V1",
            correlation_id="routing-v1",
            branch="task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
            current_head="40d28da2953b1aceed466388d217d6b88533becb",
            task_class="TEST_TRIAGE",
            agent_id="tester_agentic_v1",
            required_capabilities=("browser.uat",),
            required_tools=("playwright.browser_uat",),
        ),
        lease=lease(
            allowed_capabilities=("browser.uat",),
            allowed_tools=("playwright.browser_uat",),
            allowed_provider_ids=("playwright",),
            allowed_agent_ids=("tester_agentic_v1",),
            allowed_model_ids=(),
        ),
        providers=providers,
        models=(),
        tools=build_tool_descriptors_v1(
            providers,
            evidence_ref="routing-test",
        ),
        now=NOW,
    )

    assert decision.dispatch_allowed is False
    assert "AGENT_NOT_ADMITTED" in decision.blockers


def test_read_only_lease_blocks_source_write_route() -> None:
    providers = admitted_providers()
    decision = route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="MODEL-TOOL-AGENT-ROUTING-V1",
            correlation_id="routing-v1",
            branch="task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
            current_head="40d28da2953b1aceed466388d217d6b88533becb",
            task_class="READ_ONLY_DIAGNOSTIC",
            agent_id="coordinator_agentic_v1",
            required_capabilities=("agent.headless_api",),
            mutation_class="SOURCE_WRITE",
        ),
        lease=lease(),
        providers=providers,
        models=(),
        tools=(),
        now=NOW,
    )

    assert decision.dispatch_allowed is False
    assert "LEASE_WRITE_AUTHORITY_REQUIRED" in decision.blockers
    assert "AGENT_MUTATION_CEILING_EXCEEDED" in decision.blockers


def test_default_agent_descriptors_preserve_pending_admission_boundaries() -> None:
    by_id = {item.agent_id: item for item in default_agent_descriptors_v1()}

    assert by_id["coordinator_agentic_v1"].route_eligible is False
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False
    assert by_id["coding_builder_agentic_v1"].route_eligible is False
    assert by_id["tester_agentic_v1"].route_eligible is False
