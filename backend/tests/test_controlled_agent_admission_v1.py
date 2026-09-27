from datetime import UTC, datetime, timedelta

import pytest
from palwakf_local_agents.controlled_agent_admission_v1 import (
    ControlledAgentAdmissionReceiptV1,
    apply_controlled_agent_admission_v1,
)
from palwakf_local_agents.model_tool_agent_routing_v1 import (
    ExecutionLeaseProjectionV1,
    default_agent_descriptors_v1,
)
from pydantic import ValidationError

NOW = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)


def lease(**updates) -> ExecutionLeaseProjectionV1:
    data = {
        "project_id": "PALWAKF_AGENTIC_AI_SYSTEM",
        "task_id": "CONTROLLED-AGENT-READ-ONLY-PILOT-V1",
        "correlation_id": "controlled-agent-read-only-pilot-v1",
        "created_at": NOW,
        "provenance": ("workspace-fresh-lease",),
        "lease_id": "lease-controlled-agent-read-only-pilot-v1",
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
        "allowed_agent_ids": ("coordinator_agentic_v1",),
        "allowed_model_ids": ("qwen2.5:3b",),
        "exact_base": "9fafa7a0c2585d38e649f3bfcebe2121d4e0cf25",
        "branch": "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
        "allowed_paths": (),
        "forbidden_operations": (
            "production",
            "shared_db_mutation",
            "git_push",
            "source_write",
            "opencode_source_write",
            "hermes_bounded_write",
        ),
        "approval_reference": "CHATGPT_USER_AUTHORIZATION_CONTROLLED_AGENT_PILOT",
        "authority_scope": "WORKSPACE_GOVERNED_EXECUTION",
        "producer": "Workspace",
    }
    data.update(updates)
    return ExecutionLeaseProjectionV1.model_validate(data)


def receipt(**updates) -> ControlledAgentAdmissionReceiptV1:
    data = {
        "admission_id": "admission-coordinator-read-only-pilot-v1",
        "agent_id": "coordinator_agentic_v1",
        "created_at": NOW + timedelta(seconds=1),
        "expires_at": NOW + timedelta(minutes=20),
        "human_authority_reference": (
            "CHATGPT_USER_AUTHORIZATION_CONTROLLED_AGENT_PILOT"
        ),
        "lease_id": "lease-controlled-agent-read-only-pilot-v1",
        "exact_base": "9fafa7a0c2585d38e649f3bfcebe2121d4e0cf25",
        "branch": "task/AGENTIC-AUTONOMOUS-LOCAL-AI-MEGA-BATCH-V1",
        "allowed_capabilities": (
            "agent.headless_api",
            "model.inference",
            "model.health",
            "provider.health",
        ),
        "allowed_provider_ids": ("hermes-headless", "ollama"),
        "allowed_model_ids": ("qwen2.5:3b",),
        "allowed_tools": (),
        "evidence": ("human-authorization", "fresh-workspace-lease"),
    }
    data.update(updates)
    return ControlledAgentAdmissionReceiptV1.model_validate(data)


def test_controlled_admission_enables_only_coordinator() -> None:
    agents = apply_controlled_agent_admission_v1(
        receipt(),
        lease=lease(),
        now=NOW + timedelta(seconds=2),
    )
    by_id = {item.agent_id: item for item in agents}

    assert by_id["coordinator_agentic_v1"].route_eligible is True
    assert by_id["coordinator_agentic_v1"].mutation_ceiling == "READ_ONLY"
    assert by_id["coordinator_agentic_v1"].allowed_tools == ()
    assert by_id["sovereignty_reviewer_agentic_v1"].route_eligible is False
    assert by_id["coding_builder_agentic_v1"].route_eligible is False
    assert by_id["tester_agentic_v1"].route_eligible is False


def test_default_descriptors_still_fail_closed_without_receipt() -> None:
    by_id = {item.agent_id: item for item in default_agent_descriptors_v1()}
    assert by_id["coordinator_agentic_v1"].route_eligible is False


def test_admission_cannot_outlive_fresh_lease() -> None:
    with pytest.raises(ValueError, match="MUST_NOT_OUTLIVE_LEASE"):
        apply_controlled_agent_admission_v1(
            receipt(expires_at=NOW + timedelta(hours=1)),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_admission_rejects_expired_receipt() -> None:
    with pytest.raises(ValueError, match="AGENT_ADMISSION_EXPIRED"):
        apply_controlled_agent_admission_v1(
            receipt(expires_at=NOW + timedelta(minutes=1)),
            lease=lease(),
            now=NOW + timedelta(minutes=2),
        )


def test_admission_cannot_add_any_tool() -> None:
    with pytest.raises(
        ValidationError,
        match="READ_ONLY_AGENT_PILOT_MUST_NOT_ADMIT_TOOLS",
    ):
        receipt(allowed_tools=("opencode.engineering_analysis",))


def test_admission_cannot_expand_provider_scope() -> None:
    with pytest.raises(ValueError, match="PROVIDER_EXCEEDS_LEASE"):
        apply_controlled_agent_admission_v1(
            receipt(allowed_provider_ids=("hermes-headless", "ollama", "opencode")),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )


def test_admission_rejects_non_read_only_lease() -> None:
    bounded = lease(
        granted_scope="BOUNDED_SOURCE_WRITE",
        write_authority="BOUNDED_SOURCE_WRITE",
        allowed_paths=("backend/src/palwakf_local_agents/example.py",),
    )
    with pytest.raises(ValueError, match="REQUIRES_READ_ONLY_LEASE"):
        apply_controlled_agent_admission_v1(
            receipt(),
            lease=bounded,
            now=NOW + timedelta(seconds=2),
        )


def test_admission_must_match_workspace_human_authority_reference() -> None:
    with pytest.raises(ValueError, match="HUMAN_AUTHORITY_MISMATCH"):
        apply_controlled_agent_admission_v1(
            receipt(human_authority_reference="DIFFERENT_HUMAN_AUTHORITY_REFERENCE"),
            lease=lease(),
            now=NOW + timedelta(seconds=2),
        )
