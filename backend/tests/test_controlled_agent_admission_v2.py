from datetime import UTC, datetime, timedelta

import pytest
from palwakf_local_agents.controlled_agent_admission_v2 import (
    ControlledAgentAdmissionReceiptV2,
    apply_controlled_agent_admission_v2,
)
from palwakf_local_agents.model_tool_agent_routing_v1 import (
    ExecutionLeaseProjectionV1,
    default_agent_descriptors_v1,
)

NOW = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)


def lease(**updates) -> ExecutionLeaseProjectionV1:
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": "SOVEREIGNTY-REVIEWER-READ-ONLY-PILOT-V1",
        "correlation_id": "sovereignty-reviewer-read-only-pilot-v1",
        "created_at": NOW,
        "provenance": ("workspace-fresh-lease-v2",),
        "lease_id": "lease-sovereignty-reviewer-read-only-pilot-v1",
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
        "allowed_agent_ids": ("sovereignty_reviewer_agentic_v1",),
        "allowed_model_ids": ("palwakf-llama3.2-3b-64k:ctx64k",),
        "exact_base": "24fcec84b30f169e1877d479c2337d2a75416534",
        "branch": "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
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
        ),
        "approval_reference": (
            "CHATGPT_USER_AUTHORIZATION_20260928:"
            "SOVEREIGNTY_REVIEWER_READ_ONLY_ADMISSION_PILOT"
        ),
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    data.update(updates)
    return ExecutionLeaseProjectionV1.model_validate(data)


def receipt(**updates) -> ControlledAgentAdmissionReceiptV2:
    data = {
        "admission_id": "admission-sovereignty-reviewer-read-only-pilot-v1",
        "agent_id": "sovereignty_reviewer_agentic_v1",
        "created_at": NOW + timedelta(seconds=1),
        "expires_at": NOW + timedelta(minutes=20),
        "human_authority_reference": (
            "CHATGPT_USER_AUTHORIZATION_20260928:"
            "SOVEREIGNTY_REVIEWER_READ_ONLY_ADMISSION_PILOT"
        ),
        "lease_id": "lease-sovereignty-reviewer-read-only-pilot-v1",
        "exact_base": "24fcec84b30f169e1877d479c2337d2a75416534",
        "branch": "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
        "allowed_capabilities": (
            "agent.headless_api",
            "model.inference",
            "model.health",
            "provider.health",
        ),
        "allowed_provider_ids": ("hermes-headless", "ollama"),
        "allowed_model_ids": ("palwakf-llama3.2-3b-64k:ctx64k",),
        "allowed_tools": (),
        "allowed_task_classes": ("POLICY_REVIEW",),
        "allowed_outputs": (
            "sovereignty_review",
            "risk_register",
            "evidence_escalation",
        ),
        "evidence": (
            "human-authorization",
            "fresh-workspace-execution-lease",
            "pilot-ready-registry-role",
        ),
    }
    data.update(updates)
    return ControlledAgentAdmissionReceiptV2.model_validate(data)


def test_v2_admits_sovereignty_reviewer_only() -> None:
    agents = apply_controlled_agent_admission_v2(
        receipt(),
        lease=lease(),
        now=NOW + timedelta(seconds=2),
    )
    by_id = {item.agent_id: item for item in agents}

    reviewer = by_id["sovereignty_reviewer_agentic_v1"]
    assert reviewer.route_eligible is True
    assert reviewer.mutation_ceiling == "READ_ONLY"
    assert reviewer.allowed_tools == ()
    assert reviewer.allowed_task_classes == ("POLICY_REVIEW",)

    assert by_id["coordinator_agentic_v1"].route_eligible is False
    assert by_id["coding_builder_agentic_v1"].route_eligible is False
    assert by_id["tester_agentic_v1"].route_eligible is False


def test_v2_preserves_default_fail_closed_state_without_receipt() -> None:
    by_id = {item.agent_id: item for item in default_agent_descriptors_v1()}
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False


def test_v2_admission_cannot_outlive_lease() -> None:
    with pytest.raises(ValueError, match="MUST_NOT_OUTLIVE_LEASE"):
        apply_controlled_agent_admission_v2(
            receipt(expires_at=NOW + timedelta(hours=1)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v2_rejects_expired_receipt() -> None:
    with pytest.raises(ValueError, match="AGENT_ADMISSION_EXPIRED"):
        apply_controlled_agent_admission_v2(
            receipt(expires_at=NOW + timedelta(minutes=1)),
            lease=lease(),
            now=NOW + timedelta(minutes=2),
        )


def test_v2_rejects_provider_expansion() -> None:
    with pytest.raises(ValueError, match="PROVIDER_EXCEEDS_LEASE"):
        apply_controlled_agent_admission_v2(
            receipt(
                allowed_provider_ids=(
                    "hermes-headless",
                    "ollama",
                    "opencode",
                )
            ),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v2_rejects_task_class_not_declared_by_agent() -> None:
    with pytest.raises(ValueError, match="TASK_CLASS_NOT_DECLARED"):
        apply_controlled_agent_admission_v2(
            receipt(allowed_task_classes=("REPOSITORY_ANALYSIS",)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v2_rejects_human_authority_mismatch() -> None:
    with pytest.raises(ValueError, match="HUMAN_AUTHORITY_MISMATCH"):
        apply_controlled_agent_admission_v2(
            receipt(human_authority_reference="DIFFERENT_HUMAN_AUTHORITY_REFERENCE"),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_v2_allows_coordinator_contract_but_does_not_admit_it_here() -> None:
    coordinator_lease = lease(
        allowed_agent_ids=("coordinator_agentic_v1",),
    )
    coordinator_receipt = receipt(
        admission_id="admission-coordinator-v2-read-only",
        agent_id="coordinator_agentic_v1",
        allowed_task_classes=("TASK_PLANNING",),
        allowed_outputs=("task_brief",),
    )
    agents = apply_controlled_agent_admission_v2(
        coordinator_receipt,
        lease=coordinator_lease,
        now=NOW + timedelta(seconds=2),
    )
    by_id = {item.agent_id: item for item in agents}
    assert by_id["coordinator_agentic_v1"].route_eligible is True
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False
