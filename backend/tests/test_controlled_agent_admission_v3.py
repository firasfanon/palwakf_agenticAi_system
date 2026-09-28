from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest

from palwakf_local_agents.controlled_agent_admission_v2 import (
    ControlledAgentAdmissionReceiptV2,
)
from palwakf_local_agents.controlled_agent_admission_v3 import (
    ControlledAgentAdmissionReceiptV3,
    apply_controlled_agent_admission_v3,
)
from palwakf_local_agents.model_tool_agent_routing_v1 import (
    ExecutionLeaseProjectionV1,
    ExecutionRouteRequestV1,
    ModelDescriptorV1,
    build_tool_descriptors_v1,
    default_agent_descriptors_v1,
    route_execution_v1,
)
from palwakf_local_agents.provider_runtime_registry_v1 import ProviderRuntimeRegistryV1

NOW = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
MODEL = "palwakf-llama3.2-3b-64k:ctx64k"
BASE = "5fd1be9bc4ef23af6388fb1393167ced3ddcf83d"
BRANCH = "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1"
AUTH = "CHATGPT_USER_AUTHORIZATION_20260928:KNOWLEDGE_RESEARCHER_V3_READ_ONLY_PILOT"


def lease(**updates) -> ExecutionLeaseProjectionV1:
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": "KNOWLEDGE-RESEARCHER-READ-ONLY-PILOT-V1",
        "correlation_id": "knowledge-researcher-read-only-pilot-v1",
        "created_at": NOW,
        "provenance": ("workspace-fresh-lease-v3",),
        "lease_id": "lease-knowledge-researcher-read-only-pilot-v1",
        "granted_scope": "READ_ONLY_EXECUTION",
        "expires_at": NOW + timedelta(minutes=30),
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
        "allowed_agent_ids": ("knowledge_researcher_agentic_v1",),
        "allowed_model_ids": (MODEL,),
        "exact_base": BASE,
        "branch": BRANCH,
        "allowed_paths": (),
        "forbidden_operations": (
            "production",
            "shared_db_mutation",
            "git_push",
            "source_write",
            "opencode_source_write",
            "playwright_admission",
            "hermes_bounded_write",
            "delegation",
            "parallel_multi_agent",
            "network_access",
            "external_research",
        ),
        "approval_reference": AUTH,
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    data.update(updates)
    return ExecutionLeaseProjectionV1.model_validate(data)


def receipt(**updates) -> ControlledAgentAdmissionReceiptV3:
    data = {
        "admission_id": "admission-knowledge-researcher-read-only-pilot-v1",
        "agent_id": "knowledge_researcher_agentic_v1",
        "created_at": NOW + timedelta(seconds=1),
        "expires_at": NOW + timedelta(minutes=20),
        "human_authority_reference": AUTH,
        "lease_id": "lease-knowledge-researcher-read-only-pilot-v1",
        "exact_base": BASE,
        "branch": BRANCH,
        "allowed_capabilities": (
            "agent.headless_api",
            "model.inference",
            "model.health",
            "provider.health",
        ),
        "allowed_provider_ids": ("hermes-headless", "ollama"),
        "allowed_model_ids": (MODEL,),
        "allowed_tools": (),
        "allowed_task_classes": ("KNOWLEDGE_REVIEW",),
        "allowed_outputs": ("knowledge_review",),
        "evidence": (
            "human-authorization",
            "fresh-workspace-execution-lease-v3",
            "registry-role-admission-required-v3",
        ),
    }
    data.update(updates)
    return ControlledAgentAdmissionReceiptV3.model_validate(data)


def admitted_providers():
    registry = ProviderRuntimeRegistryV1()
    registry.record_probe(
        "hermes-headless",
        healthy=True,
        version="0.21.4",
        evidence_ref="hermes:probe",
    )
    registry.record_benchmark(
        "hermes-headless", success=True, evidence_ref="hermes:benchmark"
    )
    registry.admit(
        "hermes-headless",
        evidence_ref="hermes:admission",
        admitted_capabilities=("agent.headless_api", "provider.health"),
    )
    registry.record_probe(
        "ollama", healthy=True, version="0.34.3", evidence_ref="ollama:probe"
    )
    registry.record_benchmark("ollama", success=True, evidence_ref="ollama:benchmark")
    registry.admit(
        "ollama",
        evidence_ref="ollama:admission",
        admitted_capabilities=("model.inference", "model.health", "model.list"),
    )
    return tuple(
        registry.contract_envelope(
            provider_id,
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="KNOWLEDGE-RESEARCHER-READ-ONLY-PILOT-V1",
            correlation_id="knowledge-researcher-read-only-pilot-v1",
            provenance=("v3-test",),
            created_at=NOW,
        )
        for provider_id in ("hermes-headless", "ollama")
    )


def models():
    return (
        ModelDescriptorV1(
            model_id=MODEL,
            provider_id="ollama",
            capabilities=("model.inference",),
            health="HEALTHY",
            admitted=True,
            evidence=("ollama:model-context-gate",),
        ),
    )


def route(agents=None):
    providers = admitted_providers()
    return route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="KNOWLEDGE-RESEARCHER-READ-ONLY-PILOT-V1",
            correlation_id="knowledge-researcher-read-only-pilot-v1",
            branch=BRANCH,
            current_head=BASE,
            task_class="KNOWLEDGE_REVIEW",
            agent_id="knowledge_researcher_agentic_v1",
            required_capabilities=("agent.headless_api", "model.inference"),
            required_tools=(),
            model_required=True,
            requested_model_id=MODEL,
            mutation_class="READ_ONLY",
        ),
        lease=lease(),
        providers=providers,
        models=models(),
        tools=build_tool_descriptors_v1(providers, evidence_ref="v3-test"),
        agents=agents,
        now=NOW + timedelta(seconds=2),
    )


def test_default_descriptor_is_fail_closed_for_knowledge_researcher() -> None:
    by_id = {item.agent_id: item for item in default_agent_descriptors_v1()}
    item = by_id["knowledge_researcher_agentic_v1"]
    assert item.route_eligible is False
    assert item.allowed_tools == ()
    assert item.mutation_ceiling == "READ_ONLY"
    assert "KNOWLEDGE_REVIEW" in item.allowed_task_classes


def test_pre_admission_route_is_blocked() -> None:
    decision = route()
    assert decision.dispatch_allowed is False
    assert "AGENT_NOT_ADMITTED" in decision.blockers
    assert decision.no_authority_expansion is True


def test_v3_admits_only_knowledge_researcher() -> None:
    agents = apply_controlled_agent_admission_v3(
        receipt(), lease=lease(), now=NOW + timedelta(seconds=2)
    )
    by_id = {item.agent_id: item for item in agents}
    assert by_id["knowledge_researcher_agentic_v1"].route_eligible is True
    assert by_id["knowledge_researcher_agentic_v1"].allowed_tools == ()
    assert by_id["knowledge_researcher_agentic_v1"].allowed_task_classes == (
        "KNOWLEDGE_REVIEW",
    )
    assert by_id["coordinator_agentic_v1"].route_eligible is False
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False
    assert by_id["coding_builder_agentic_v1"].route_eligible is False
    assert by_id["tester_agentic_v1"].route_eligible is False


def test_post_admission_route_is_allowed_read_only() -> None:
    agents = apply_controlled_agent_admission_v3(
        receipt(), lease=lease(), now=NOW + timedelta(seconds=2)
    )
    decision = route(agents)
    assert decision.dispatch_allowed is True
    assert decision.blockers == ()
    assert decision.execution_provider_id == "hermes-headless"
    assert decision.model_provider_id == "ollama"
    assert decision.model_id == MODEL
    assert decision.tool_ids == ()
    assert decision.mutation_class == "READ_ONLY"
    assert decision.no_authority_expansion is True


def test_v3_rejects_provider_expansion() -> None:
    with pytest.raises(ValueError, match="PROVIDER_EXCEEDS_LEASE"):
        apply_controlled_agent_admission_v3(
            receipt(allowed_provider_ids=("hermes-headless", "ollama", "opencode")),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v3_rejects_task_class_expansion() -> None:
    with pytest.raises(ValueError, match="TASK_CLASS_NOT_DECLARED"):
        apply_controlled_agent_admission_v3(
            receipt(allowed_task_classes=("REPOSITORY_ANALYSIS",)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v3_rejects_tool_expansion() -> None:
    with pytest.raises(ValueError, match="READ_ONLY_AGENT_V3_MUST_NOT_ADMIT_TOOLS"):
        receipt(allowed_tools=("opencode.engineering_analysis",))


def test_v3_rejects_write_lease() -> None:
    write_lease = lease(
        granted_scope="BOUNDED_SOURCE_WRITE",
        write_authority="BOUNDED_SOURCE_WRITE",
        allowed_paths=("backend/src",),
    )
    with pytest.raises(ValueError, match="REQUIRES_READ_ONLY_LEASE"):
        apply_controlled_agent_admission_v3(
            receipt(), lease=write_lease, now=NOW + timedelta(seconds=2)
        )


def test_v3_rejects_human_authority_mismatch() -> None:
    with pytest.raises(ValueError, match="HUMAN_AUTHORITY_MISMATCH"):
        apply_controlled_agent_admission_v3(
            receipt(human_authority_reference="DIFFERENT_HUMAN_AUTHORITY_REFERENCE"),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v3_admission_cannot_outlive_lease() -> None:
    with pytest.raises(ValueError, match="MUST_NOT_OUTLIVE_LEASE"):
        apply_controlled_agent_admission_v3(
            receipt(expires_at=NOW + timedelta(hours=1)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v2_agent_id_contract_remains_immutable() -> None:
    allowed = set(get_args(ControlledAgentAdmissionReceiptV2.model_fields["agent_id"].annotation))
    assert allowed == {
        "coordinator_agentic_v1",
        "sovereignty_reviewer_agentic_v1",
    }
