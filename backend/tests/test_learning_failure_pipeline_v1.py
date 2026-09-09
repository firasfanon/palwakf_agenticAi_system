from __future__ import annotations

import pytest

from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ProviderId,
    RunReceipt,
)
from palwakf_local_agents.agentic_core_v1.learning import (
    EvaluationEngine,
    LearningEngine,
)

PROJECT_ID = "PALWAKF_LOCAL_AGENTS"
TASK_ID = "FAILURE_TO_LEARNING_PREVENTIVE_ENFORCEMENT_V1"


def _authorization(
    *,
    project_id: str = PROJECT_ID,
    task_id: str = TASK_ID,
) -> AuthorizationEnvelope:
    return AuthorizationEnvelope(
        authorization_id="auth-failure-learning-v1",
        issuer="WORKSPACE_MANAGER",
        project_id=project_id,
        task_id=task_id,
        allowed_agent_ids=["agent-test"],
        allowed_task_classes=["READ_ONLY_DIAGNOSTIC"],
        allowed_provider_ids=[ProviderId.NATIVE],
        allowed_model_providers=["none"],
        allowed_filesystem_roots=[],
        allowed_path_patterns=["**"],
        read_only=True,
        allow_network_read=False,
        allow_network_write=False,
    )


def _receipt(
    *,
    final_result: str,
    changed_files: list[str] | None = None,
    errors: list[dict] | None = None,
) -> RunReceipt:
    return RunReceipt(
        project_id=PROJECT_ID,
        task_id=TASK_ID,
        state_package_id="state-failure-learning-v1",
        agent_id="agent-test",
        role_id="role-test",
        skill_ids=[],
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        model_id=None,
        tools=[],
        environment={},
        base_sha="a" * 40,
        before_head="b" * 40,
        authorized_scope={"read_only": True},
        plan=[],
        actions=[],
        observations=[],
        changed_files=list(changed_files or []),
        tests=[],
        errors=list(errors or []),
        retries=0,
        evidence=[
            {
                "type": "RUN_RECEIPT_JSON",
                "path": "evidence/run-failure-learning-v1.json",
            }
        ],
        final_result=final_result,
        next_action="EXTERNAL_REVIEW_REQUIRED",
    )


def _failure_metadata(candidate) -> dict:
    matches = [
        item
        for item in candidate.evidence_refs
        if item.get("type") == "FAILURE_CLASSIFICATION"
    ]
    assert len(matches) == 1
    return matches[0]


def _evaluation_metadata(candidate) -> dict:
    matches = [
        item
        for item in candidate.evidence_refs
        if item.get("type") == "EVALUATION_RECEIPT"
    ]
    assert len(matches) == 1
    return matches[0]


def test_policy_failure_generates_lesson_and_preventive_gate_candidate():
    receipt = _receipt(
        final_result="FAIL",
        changed_files=["backend/unauthorized-change.py"],
    )
    evaluation = EvaluationEngine().evaluate(receipt)
    assert evaluation.passed is False
    assert "PROJECT_MUTATION_OBSERVED" in evaluation.reasons

    candidates = LearningEngine().derive(
        receipt=receipt,
        evaluation=evaluation,
        authorization=_authorization(),
    )

    assert [candidate.candidate_type for candidate in candidates] == [
        "PROJECT_LESSON",
        "PREVENTIVE_GATE_CANDIDATE",
    ]
    assert all(
        candidate.promotion_status == "EXTERNAL_REVIEW_REQUIRED"
        for candidate in candidates
    )
    for candidate in candidates:
        failure = _failure_metadata(candidate)
        assert failure["classification"] == "POLICY_FAILURE"
        assert failure["confidence"] == "HIGH"
        assert failure["root_cause"] == "PROJECT_MUTATION_OBSERVED"
        assert failure["preventive_gate_allowed"] is True
        evidence = _evaluation_metadata(candidate)
        assert evidence["evaluation_id"] == evaluation.evaluation_id
        assert evidence["passed"] is False
        assert "PROJECT_MUTATION_OBSERVED" in evidence["reasons"]


def test_unknown_failure_generates_lesson_without_preventive_gate():
    receipt = _receipt(
        final_result="FAIL",
        errors=[{"code": "UNCLASSIFIED_RUNTIME_FAILURE"}],
    )
    evaluation = EvaluationEngine().evaluate(receipt)
    assert evaluation.passed is False
    assert "ERRORS_PRESENT" in evaluation.reasons

    candidates = LearningEngine().derive(
        receipt=receipt,
        evaluation=evaluation,
        authorization=_authorization(),
    )

    assert [candidate.candidate_type for candidate in candidates] == ["PROJECT_LESSON"]
    assert _failure_metadata(candidates[0]) == {
        "type": "FAILURE_CLASSIFICATION",
        "classification": "UNKNOWN_FAILURE",
        "confidence": "LOW",
        "root_cause": "UNRESOLVED",
        "preventive_gate_allowed": False,
    }


def test_cross_project_learning_still_fails_closed_before_classification():
    receipt = _receipt(
        final_result="FAIL",
        changed_files=["backend/unauthorized-change.py"],
    )
    evaluation = EvaluationEngine().evaluate(receipt)
    with pytest.raises(ValueError, match="LEARNING_CROSS_PROJECT_DENIED"):
        LearningEngine().derive(
            receipt=receipt,
            evaluation=evaluation,
            authorization=_authorization(project_id="OTHER_PROJECT"),
        )


def test_task_mismatch_still_fails_closed_before_classification():
    receipt = _receipt(
        final_result="FAIL",
        changed_files=["backend/unauthorized-change.py"],
    )
    evaluation = EvaluationEngine().evaluate(receipt)
    with pytest.raises(ValueError, match="LEARNING_TASK_AUTHORITY_MISMATCH"):
        LearningEngine().derive(
            receipt=receipt,
            evaluation=evaluation,
            authorization=_authorization(task_id="OTHER_TASK"),
        )


def test_pass_behavior_remains_single_external_review_project_lesson():
    receipt = _receipt(final_result="PASS")
    evaluation = EvaluationEngine().evaluate(receipt)
    assert evaluation.passed is True

    candidates = LearningEngine().derive(
        receipt=receipt,
        evaluation=evaluation,
        authorization=_authorization(),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_type == "PROJECT_LESSON"
    assert candidate.promotion_status == "EXTERNAL_REVIEW_REQUIRED"
    assert candidate.evidence_refs == receipt.evidence
