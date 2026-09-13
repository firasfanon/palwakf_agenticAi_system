import pytest
from pydantic import ValidationError

from palwakf_local_agents.agentic_core_v1.pre_l5_cross_system_contract import (
    WorkspacePreL5CrossSystemContractV1,
    build_agentic_pre_l5_context,
    build_mind_review_context_wire,
)


PROJECT = "PALWAKF_LOCAL_AGENTS"
TASK = "TASK-CROSS-SYSTEM"
STATE = "workspace-state-cross-system"
RUN = "RUN-CROSS-SYSTEM"


def payload():
    return {
        "contract_version":
            "PALWAKF_PRE_L5_CROSS_SYSTEM_CONTRACT_V1",
        "project_id": PROJECT,
        "task_id": TASK,
        "state_package_id": STATE,
        "execution_run_id": RUN,
        "authority_reference": "AUTH:CROSS-SYSTEM",
        "authority_package": {
            "state_package_id": STATE,
            "execution_run_id": RUN,
            "project_id": PROJECT,
            "task_id": TASK,
            "repository": "example/repo",
            "task_branch": "task/CROSS-SYSTEM",
            "base_sha": "1" * 40,
            "expected_head": "2" * 40,
            "authority_reference": "AUTH:CROSS-SYSTEM",
            "objective":
                "Execute governed cross-system pre-L5 proof.",
            "constraints": ["READ_ONLY"],
            "timeout_seconds": 60,
            "scope_patterns": ["**"],
            "read_only": True,
            "allow_network_read": False,
            "allow_network_write": False,
            "required_capabilities": [],
            "required_tests": ["PRE_L5_CROSS_SYSTEM"],
            "requested_provider_id":
                "PALWAKF_NATIVE_AGENT",
            "requested_model_provider": "none",
            "contract_version":
                "PALWAKF_INTERSYSTEM_CONTRACT_V1",
        },
        "active_instruction_set_sha256":
            "a" * 64,
        "active_instructions": [
            {
                "instruction_id": "AMENDMENT-20260913",
                "authority": "GLOBAL_CROSS_PROJECT",
                "version": "V1",
                "effective_at":
                    "2026-09-13T00:00:00+00:00",
                "applies_to_projects": [PROJECT],
                "supersedes": ["OLD-INSTRUCTION"],
            }
        ],
        "instruction_exclusions": [
            {
                "instruction_id": "OLD-INSTRUCTION",
                "reason":
                    "SUPERSEDED_BY_ACTIVE_INSTRUCTION",
            }
        ],
        "active_lesson_ids": ["LESSON-1"],
        "reused_lesson_ids": ["LESSON-1"],
        "known_failure_fingerprints": [
            {
                "fingerprint_id": "FP-1",
                "lesson_id": "LESSON-1",
                "preventive_gate_id": "GATE-1",
                "relevant": True,
                "applies_to_projects": [PROJECT],
            }
        ],
        "applicable_skill_ids": ["SKILL-1"],
        "preventive_gate_ids": ["GATE-1"],
        "execution_admission": "READY",
        "canonical_promotion_allowed": False,
    }


def test_workspace_contract_binds_to_agentic_context():
    contract = (
        WorkspacePreL5CrossSystemContractV1
        .model_validate(payload())
    )

    context = build_agentic_pre_l5_context(
        contract
    )

    assert (
        context
        .active_instruction_set
        .project_id
        == PROJECT
    )

    assert (
        context
        .active_instruction_set
        .authorization_id
        == f"intersystem:{RUN}"
    )

    assert (
        context
        .lesson_reuse
        .reused_lesson_ids
        == ("LESSON-1",)
    )


def test_stale_instruction_cannot_reenter_active_context():
    value = payload()
    value["active_instructions"].append(
        {
            "instruction_id": "OLD-INSTRUCTION",
            "authority": "OLD",
            "version": "OLD",
            "effective_at":
                "2026-09-10T00:00:00+00:00",
            "applies_to_projects": [PROJECT],
            "supersedes": [],
        }
    )

    with pytest.raises(
        ValidationError,
        match="AGENTIC_STALE_INSTRUCTION_REENTRY",
    ):
        (
            WorkspacePreL5CrossSystemContractV1
            .model_validate(value)
        )


def test_workspace_project_binding_tamper_fails():
    value = payload()
    value["project_id"] = "OTHER_PROJECT"

    with pytest.raises(
        ValidationError,
        match="AGENTIC_WORKSPACE_PROJECT_BINDING_MISMATCH",
    ):
        (
            WorkspacePreL5CrossSystemContractV1
            .model_validate(value)
        )


def test_mind_review_context_carries_workspace_digest():
    contract = (
        WorkspacePreL5CrossSystemContractV1
        .model_validate(payload())
    )

    mind = build_mind_review_context_wire(
        contract=contract,
        run_id="run-proof",
    )

    assert (
        mind.active_instruction_set_sha256
        == contract.active_instruction_set_sha256
    )

    assert mind.canonical_write_allowed is False
    assert mind.project_id == PROJECT
    assert mind.task_id == TASK
