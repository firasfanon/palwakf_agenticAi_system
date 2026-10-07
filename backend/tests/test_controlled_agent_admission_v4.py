from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest

from palwakf_local_agents.controlled_agent_admission_v3 import (
    ControlledAgentAdmissionReceiptV3,
)
from palwakf_local_agents.controlled_agent_admission_v4 import (
    VISUAL_QA_CAPABILITIES,
    VISUAL_QA_RUNTIME_TASK_CLASSES,
    VISUAL_QA_TOOLS,
    ControlledAgentAdmissionReceiptV4,
    apply_controlled_agent_admission_v4,
)
from palwakf_local_agents.model_tool_agent_routing_v1 import (
    ExecutionLeaseProjectionV1,
    ExecutionRouteRequestV1,
    build_tool_descriptors_v1,
    default_agent_descriptors_v1,
    route_execution_v1,
)
from palwakf_local_agents.provider_runtime_registry_v1 import ProviderRuntimeRegistryV1

NOW = datetime(2026, 10, 7, 0, 0, tzinfo=UTC)
BASE = "a79d114f169a49fc509144d8e15dfdb0cae005a2"
BRANCH = "task/P6-VISUAL-QA-CONTROLLED-ADMISSION-V4-V1"
AUTH = "CHATGPT_USER_AUTHORIZATION_20261007:P6_VISUAL_QA_V4_READ_ONLY_PILOT"
TASK = "P6-VISUAL-QA-READ-ONLY-PILOT-V1"
CORRELATION = "p6-visual-qa-read-only-pilot-v1"


def lease(**updates) -> ExecutionLeaseProjectionV1:
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": TASK,
        "correlation_id": CORRELATION,
        "created_at": NOW,
        "provenance": ("workspace-fresh-lease-v4",),
        "lease_id": "lease-p6-visual-qa-read-only-pilot-v1",
        "granted_scope": "READ_ONLY_EXECUTION",
        "expires_at": NOW + timedelta(minutes=30),
        "allowed_capabilities": VISUAL_QA_CAPABILITIES,
        "allowed_tools": VISUAL_QA_TOOLS,
        "write_authority": "NONE",
        "revocation_state": "ACTIVE",
        "allowed_provider_ids": ("playwright",),
        "allowed_agent_ids": ("tester_agentic_v1",),
        "allowed_model_ids": (),
        "exact_base": BASE,
        "branch": BRANCH,
        "allowed_paths": (),
        "forbidden_operations": (
            "production",
            "shared_db_mutation",
            "git_push",
            "source_write",
            "opencode_source_write",
            "hermes_bounded_write",
            "delegation",
            "parallel_multi_agent",
            "network_write",
            "form_submission",
            "upload",
            "download_side_effect",
        ),
        "approval_reference": AUTH,
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    data.update(updates)
    return ExecutionLeaseProjectionV1.model_validate(data)


def receipt(**updates) -> ControlledAgentAdmissionReceiptV4:
    data = {
        "admission_id": "admission-p6-visual-qa-read-only-pilot-v1",
        "agent_id": "tester_agentic_v1",
        "created_at": NOW + timedelta(seconds=1),
        "expires_at": NOW + timedelta(minutes=20),
        "human_authority_reference": AUTH,
        "lease_id": "lease-p6-visual-qa-read-only-pilot-v1",
        "exact_base": BASE,
        "branch": BRANCH,
        "allowed_capabilities": VISUAL_QA_CAPABILITIES,
        "allowed_provider_ids": ("playwright",),
        "allowed_model_ids": (),
        "allowed_tools": VISUAL_QA_TOOLS,
        "allowed_task_classes": VISUAL_QA_RUNTIME_TASK_CLASSES,
        "allowed_outputs": ("visual_qa_report",),
        "playwright_admission_allowed": True,
        "evidence": (
            "human-authorization",
            "fresh-workspace-execution-lease-v4",
            "tester-agentic-v1-visual-qa-role-mapping",
        ),
    }
    data.update(updates)
    return ControlledAgentAdmissionReceiptV4.model_validate(data)


def admitted_playwright_provider():
    registry = ProviderRuntimeRegistryV1()
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
        admitted_capabilities=VISUAL_QA_CAPABILITIES,
    )
    return registry.contract_envelope(
        "playwright",
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        task_id=TASK,
        correlation_id=CORRELATION,
        provenance=("p6-v4-test",),
        created_at=NOW,
    )


def route(agents=None):
    providers = (admitted_playwright_provider(),)
    return route_execution_v1(
        ExecutionRouteRequestV1(
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id=TASK,
            correlation_id=CORRELATION,
            branch=BRANCH,
            current_head=BASE,
            task_class="TEST_TRIAGE",
            agent_id="tester_agentic_v1",
            required_capabilities=VISUAL_QA_CAPABILITIES,
            required_tools=VISUAL_QA_TOOLS,
            model_required=False,
            mutation_class="READ_ONLY",
        ),
        lease=lease(),
        providers=providers,
        models=(),
        tools=build_tool_descriptors_v1(providers, evidence_ref="p6-v4-test"),
        agents=agents,
        now=NOW + timedelta(seconds=2),
    )


def test_default_descriptor_is_fail_closed_for_visual_qa_tester() -> None:
    by_id = {item.agent_id: item for item in default_agent_descriptors_v1()}
    item = by_id["tester_agentic_v1"]
    assert item.route_eligible is False
    assert item.allowed_tools == VISUAL_QA_TOOLS
    assert item.allowed_provider_ids == ("playwright",)
    assert item.allowed_task_classes == ("TEST_TRIAGE",)
    assert item.mutation_ceiling == "READ_ONLY"


def test_pre_admission_route_is_blocked() -> None:
    decision = route()
    assert decision.dispatch_allowed is False
    assert decision.blockers == ("AGENT_NOT_ADMITTED",)
    assert decision.no_authority_expansion is True


def test_v4_admits_only_visual_qa_tester_with_exact_scope() -> None:
    agents = apply_controlled_agent_admission_v4(
        receipt(),
        lease=lease(),
        now=NOW + timedelta(seconds=2),
    )
    by_id = {item.agent_id: item for item in agents}
    tester = by_id["tester_agentic_v1"]
    assert tester.route_eligible is True
    assert tester.capabilities == VISUAL_QA_CAPABILITIES
    assert tester.allowed_tools == VISUAL_QA_TOOLS
    assert tester.allowed_provider_ids == ("playwright",)
    assert tester.allowed_task_classes == ("TEST_TRIAGE",)
    assert tester.mutation_ceiling == "READ_ONLY"
    assert by_id["coordinator_agentic_v1"].route_eligible is False
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False
    assert by_id["knowledge_researcher_agentic_v1"].route_eligible is False
    assert by_id["coding_builder_agentic_v1"].route_eligible is False


def test_post_admission_route_is_allowed_read_only() -> None:
    agents = apply_controlled_agent_admission_v4(
        receipt(),
        lease=lease(),
        now=NOW + timedelta(seconds=2),
    )
    decision = route(agents)
    assert decision.dispatch_allowed is True
    assert decision.blockers == ()
    assert decision.execution_provider_id is None
    assert decision.model_provider_id is None
    assert decision.model_id is None
    assert decision.tool_ids == VISUAL_QA_TOOLS
    assert decision.provider_ids == ("playwright",)
    assert decision.capability_ids == VISUAL_QA_CAPABILITIES
    assert decision.mutation_class == "READ_ONLY"
    assert decision.no_authority_expansion is True


def test_v4_requires_explicit_playwright_admission() -> None:
    with pytest.raises(ValueError, match="VISUAL_QA_PLAYWRIGHT_ADMISSION_REQUIRED"):
        receipt(playwright_admission_allowed=False)


@pytest.mark.parametrize(
    "tools",
    [
        VISUAL_QA_TOOLS[:2],
        VISUAL_QA_TOOLS + ("playwright.browser_mutation",),
    ],
)
def test_v4_rejects_any_playwright_tool_scope_drift(tools) -> None:
    with pytest.raises(ValueError, match="VISUAL_QA_PLAYWRIGHT_TOOL_SCOPE_MISMATCH"):
        receipt(allowed_tools=tools)


def test_v4_rejects_provider_scope_drift() -> None:
    with pytest.raises(ValueError, match="VISUAL_QA_PROVIDER_SCOPE_MISMATCH"):
        receipt(allowed_provider_ids=("playwright", "hermes-headless"))


def test_v4_rejects_capability_scope_drift() -> None:
    with pytest.raises(ValueError, match="VISUAL_QA_CAPABILITY_SCOPE_MISMATCH"):
        receipt(allowed_capabilities=("browser.uat",))


def test_v4_rejects_canonical_label_as_unregistered_runtime_task_class() -> None:
    with pytest.raises(ValueError, match="VISUAL_QA_RUNTIME_TASK_CLASS_MISMATCH"):
        receipt(allowed_task_classes=("VISUAL_QA_REVIEW",))


def test_v4_rejects_playwright_tools_for_non_visual_agent() -> None:
    with pytest.raises(ValueError, match="PLAYWRIGHT_ADMISSION_ONLY_FOR_VISUAL_QA"):
        receipt(
            agent_id="coordinator_agentic_v1",
            playwright_admission_allowed=True,
        )


def test_v4_rejects_tool_scope_lease_mismatch() -> None:
    smaller_lease = lease(allowed_tools=VISUAL_QA_TOOLS[:2])
    with pytest.raises(ValueError, match="AGENT_ADMISSION_TOOL_SCOPE_MISMATCH"):
        apply_controlled_agent_admission_v4(
            receipt(),
            lease=smaller_lease,
            now=NOW + timedelta(seconds=2),
        )


def test_v4_rejects_write_lease() -> None:
    write_lease = lease(
        granted_scope="BOUNDED_SOURCE_WRITE",
        write_authority="BOUNDED_SOURCE_WRITE",
        allowed_paths=("backend/src",),
    )
    with pytest.raises(ValueError, match="REQUIRES_READ_ONLY_LEASE"):
        apply_controlled_agent_admission_v4(
            receipt(),
            lease=write_lease,
            now=NOW + timedelta(seconds=2),
        )


def test_v4_rejects_human_authority_mismatch() -> None:
    with pytest.raises(ValueError, match="HUMAN_AUTHORITY_MISMATCH"):
        apply_controlled_agent_admission_v4(
            receipt(human_authority_reference="DIFFERENT_HUMAN_AUTHORITY_REFERENCE"),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v4_admission_cannot_outlive_lease() -> None:
    with pytest.raises(ValueError, match="MUST_NOT_OUTLIVE_LEASE"):
        apply_controlled_agent_admission_v4(
            receipt(expires_at=NOW + timedelta(hours=1)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v3_agent_id_contract_remains_immutable() -> None:
    allowed = set(
        get_args(ControlledAgentAdmissionReceiptV3.model_fields["agent_id"].annotation)
    )
    assert allowed == {
        "coordinator_agentic_v1",
        "sovereignty_reviewer_agentic_v1",
        "knowledge_researcher_agentic_v1",
    }
    assert "tester_agentic_v1" not in allowed
