from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from palwakf_local_agents.agentic_core_v1 import provider_learning
from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunReceipt,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.external_contracts import (
    WorkspaceStatePackage,
)
from palwakf_local_agents.agentic_core_v1.learning import (
    ExperienceStore,
    LearningCandidate,
    MindReviewEnvelope,
)
from palwakf_local_agents.agentic_core_v1.learning_service import (
    AgenticLearningService,
)
from palwakf_local_agents.agentic_core_v1.pre_l5_enforcement import (
    ActiveGoverningInstructionSetV1,
    ActiveInstructionV1,
    FivePartExecutionEvidenceV1,
    KnownFailureFingerprintV1,
    LessonReuseProofV1,
    PreL5BootstrapContextV1,
    PreL5ExecutionGuard,
    ProviderModelCapabilityProofV1,
    ProviderModelRequirementsV1,
)


PROJECT = "PALWAKF_LOCAL_AGENTS"
TASK = "TASK-PRE-L5-ENFORCEMENT"
STATE = "STATE-PRE-L5-ENFORCEMENT"
AUTH = "AUTH-PRE-L5-ENFORCEMENT"


def active_set(
    *,
    projects=(PROJECT,),
    conflicts=(),
):
    return ActiveGoverningInstructionSetV1(
        project_id=PROJECT,
        task_id=TASK,
        state_package_id=STATE,
        authorization_id=AUTH,
        active_instructions=(
            ActiveInstructionV1(
                instruction_id="AMENDMENT-20260913",
                authority="GLOBAL_CROSS_PROJECT",
                version="V1",
                effective_at="2026-09-13T00:00:00Z",
                applies_to_projects=projects,
                supersedes=("OLD-PRE-L5-INSTRUCTION",),
            ),
        ),
        historical_excluded_ids=(
            "OLD-PRE-L5-INSTRUCTION",
        ),
        revoked_excluded_ids=(
            "REVOKED-001",
        ),
        conflicts=conflicts,
    )


def lesson_reuse(
    *,
    reused=("LESSON-TRANSPORT-INTEGRITY",),
):
    return LessonReuseProofV1(
        active_lesson_ids=(
            "LESSON-TRANSPORT-INTEGRITY",
        ),
        reused_lesson_ids=reused,
        known_failure_fingerprints=(
            KnownFailureFingerprintV1(
                fingerprint_id=(
                    "RAW_IDENTIFIER_CHAT_TRANSPORT_CORRUPTION"
                ),
                lesson_id=(
                    "LESSON-TRANSPORT-INTEGRITY"
                ),
                preventive_gate_id=(
                    "PALWAKF_CHAT_TRANSPORT_"
                    "IDENTIFIER_INTEGRITY_GATE_V1"
                ),
                applies_to_projects=(PROJECT,),
            ),
        ),
    )


def context():
    return PreL5BootstrapContextV1(
        active_instruction_set=active_set(),
        lesson_reuse=lesson_reuse(),
    )


def requirements():
    return ProviderModelRequirementsV1(
        min_context_window=1,
        reasoning_required=False,
        required_endpoint_modes=(
            "NATIVE_RUNTIME",
        ),
        required_tool_capabilities=(
            "repository_manifest_read",
        ),
        required_agent_capabilities=(
            "READ_ONLY_DIAGNOSTIC",
        ),
        required_locality="LOCAL_ONLY",
        required_privacy="LOCAL_ONLY",
    )


def capability():
    return ProviderModelCapabilityProofV1(
        provider_id=ProviderId.NATIVE,
        model_provider="none",
        model_id=None,
        context_window=1,
        reasoning_capable=False,
        endpoint_modes=(
            "NATIVE_RUNTIME",
        ),
        tool_capabilities=(
            "repository_manifest_read",
        ),
        agent_capabilities=(
            "READ_ONLY_DIAGNOSTIC",
        ),
        locality="LOCAL",
        privacy="LOCAL",
    )


def guard():
    return PreL5ExecutionGuard(
        context=context(),
        requirements=requirements(),
        capability_proof=capability(),
    )


def request(tmp_path: Path) -> RunRequest:
    agent_id = "agent-pre-l5"

    auth = AuthorizationEnvelope(
        authorization_id=AUTH,
        issuer="WORKSPACE_MANAGER",
        project_id=PROJECT,
        task_id=TASK,
        allowed_agent_ids=[agent_id],
        allowed_task_classes=[
            "READ_ONLY_DIAGNOSTIC",
        ],
        allowed_provider_ids=[
            ProviderId.NATIVE,
        ],
        allowed_model_providers=["none"],
        allowed_tools=[
            "repository_manifest_read",
        ],
        allowed_filesystem_roots=[
            str(tmp_path),
        ],
        allowed_path_patterns=["**"],
        read_only=True,
        allow_network_read=False,
        allow_network_write=False,
    )

    env = ExecutionEnvironment(
        project_id=PROJECT,
        repository=(
            "firasfanon/palwakf_agenticAi_system"
        ),
        task_branch=(
            "task/AGENTIC-L4-WIP-PRE-L5-"
            "ENFORCEMENT-V1"
        ),
        base_sha="1" * 40,
        expected_head="2" * 40,
        worktree=str(tmp_path),
        filesystem_policy=FilesystemPolicy(
            mode="READ_ONLY",
            allowed_roots=[
                str(tmp_path),
            ],
            allowed_patterns=["**"],
        ),
        network_policy=NetworkPolicy(
            read=False,
            write=False,
        ),
        tool_policy=[
            "repository_manifest_read",
        ],
    )

    return RunRequest(
        project_id=PROJECT,
        task_id=TASK,
        state_package_id=STATE,
        agent_id=agent_id,
        role_id="ROLE-PRE-L5",
        task_class="READ_ONLY_DIAGNOSTIC",
        objective="Governed pre-L5 diagnostic.",
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        model_id=None,
        skill_ids=[],
        tools=[
            "repository_manifest_read",
        ],
        authorization=auth,
        environment=env,
    )


def receipt(
    *,
    tool_execution_success=True,
    tool_call_observed=True,
) -> RunReceipt:
    return RunReceipt(
        project_id=PROJECT,
        task_id=TASK,
        state_package_id=STATE,
        agent_id="agent-pre-l5",
        role_id="ROLE-PRE-L5",
        skill_ids=[],
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        model_id=None,
        tools=[
            "repository_manifest_read",
        ],
        environment={},
        base_sha="1" * 40,
        before_head="2" * 40,
        authorized_scope={},
        plan=[],
        actions=[
            {
                "type":
                    "READ_ONLY_REPOSITORY_MANIFEST",
                "process_success": True,
                "policy_success": True,
                "tool_execution_success":
                    tool_execution_success,
                "objective_success": True,
                "postcondition_success": True,
                "tool_call_observed":
                    tool_call_observed,
            }
        ],
        observations=[],
        changed_files=[],
        tests=[],
        errors=[],
        retries=0,
        evidence=[],
        final_result="PASS",
        next_action="EXTERNAL_REVIEW_REQUIRED",
    )


def test_active_instruction_filtering_and_stale_exclusion():
    resolved = active_set()

    assert [
        item.instruction_id
        for item in resolved.active_instructions
    ] == ["AMENDMENT-20260913"]

    assert (
        "OLD-PRE-L5-INSTRUCTION"
        in resolved.historical_excluded_ids
    )

    with pytest.raises(ValidationError):
        ActiveInstructionV1(
            instruction_id="OLD",
            authority="HISTORICAL",
            version="OLD",
            effective_at="2026-09-10T00:00:00Z",
            status="SUPERSEDED",
        )


def test_active_instruction_conflict_fails_closed():
    with pytest.raises(
        ValidationError,
        match="CONFLICTING_ACTIVE_INSTRUCTIONS",
    ):
        active_set(
            conflicts=(
                "NEW_VS_OLD",
            )
        )


def test_known_failure_requires_active_reused_lesson():
    with pytest.raises(
        ValidationError,
        match="KNOWN_RELEVANT_LESSON_NOT_REUSED",
    ):
        lesson_reuse(reused=())


def test_provider_model_capability_intersection(tmp_path):
    req = request(tmp_path)

    guard().validate_before(req)

    bad_proof = capability().model_copy(
        update={
            "context_window": 1,
        }
    )

    strict_requirements = requirements().model_copy(
        update={
            "min_context_window": 64000,
        }
    )

    strict_guard = PreL5ExecutionGuard(
        context=context(),
        requirements=strict_requirements,
        capability_proof=bad_proof,
    )

    with pytest.raises(
        ValueError,
        match="MODEL_CONTEXT_WINDOW_INSUFFICIENT",
    ):
        strict_guard.validate_before(req)


def test_tool_call_observed_is_not_tool_execution_success():
    evidence = FivePartExecutionEvidenceV1(
        process_success=True,
        policy_success=True,
        tool_execution_success=False,
        objective_success=True,
        postcondition_success=True,
        tool_call_observed=True,
    )

    assert evidence.trustworthy_pass is False

    with pytest.raises(
        ValueError,
        match="FIVE_PART_EXECUTION_EVIDENCE_FAIL",
    ):
        guard().validate_after(
            receipt(
                tool_execution_success=False,
                tool_call_observed=True,
            )
        )

    assert (
        guard()
        .validate_after(receipt())
        .trustworthy_pass
        is True
    )


def test_restart_resume_preserves_only_resolved_current_set():
    original = context()

    serialized = original.model_dump_json()

    resumed = (
        PreL5BootstrapContextV1
        .model_validate_json(serialized)
    )

    assert (
        resumed.instruction_set_digest()
        == original.instruction_set_digest()
    )

    active_ids = {
        item.instruction_id
        for item in (
            resumed
            .active_instruction_set
            .active_instructions
        )
    }

    assert "OLD-PRE-L5-INSTRUCTION" not in active_ids
    assert "REVOKED-001" not in active_ids


def test_cross_project_instruction_leakage_fails_closed():
    with pytest.raises(
        ValidationError,
        match=(
            "INSTRUCTION_PROJECT_"
            "APPLICABILITY_MISMATCH"
        ),
    ):
        active_set(
            projects=("OTHER_PROJECT",)
        )


def test_no_automatic_canonical_promotion():
    candidate = LearningCandidate(
        project_id=PROJECT,
        task_id=TASK,
        source_run_id="run-1",
        candidate_type="PROJECT_LESSON",
        statement="Candidate only.",
        rationale="External review required.",
        evidence_refs=[],
    )

    review = MindReviewEnvelope(
        project_id=PROJECT,
        candidate_ids=[
            candidate.candidate_id,
        ],
    )

    guard().validate_learning_outputs(
        candidates=[candidate],
        mind_review=review,
    )

    assert candidate.promotion_status == (
        "EXTERNAL_REVIEW_REQUIRED"
    )

    assert (
        review.accepted_project_knowledge
        is False
    )


def test_ollama_hermes_learning_pipeline_remains_candidate_only(
    monkeypatch,
    tmp_path,
):
    class FakeOllama:
        endpoint = "http://127.0.0.1:11434"

        def health(self):
            return {
                "provider_id": "ollama",
                "healthy": True,
                "models": ["qwen-test"],
                "latency_ms": 1.0,
                "locality": "LOCAL_ENDPOINT",
            }

    class FakeHermes:
        def health(self):
            return {
                "provider_id": "HERMES_AGENT",
                "discovered": True,
                "healthy": True,
                "certification":
                    "EXTERNAL_CERTIFICATION_"
                    "EVIDENCE_REQUIRED",
            }

    monkeypatch.setattr(
        provider_learning,
        "OllamaProvider",
        FakeOllama,
    )

    monkeypatch.setattr(
        provider_learning,
        "HermesProvider",
        FakeHermes,
    )

    learning = SimpleNamespace(
        store=ExperienceStore(
            root=tmp_path / "learning"
        )
    )

    package = SimpleNamespace(
        required_capabilities=[
            "OLLAMA_PROVIDER_LEARNING",
            "HERMES_PROVIDER_LEARNING",
        ],
        allow_network_read=True,
        project_id=PROJECT,
        task_id=TASK,
    )

    output = provider_learning.collect_provider_learning(
        learning=learning,
        package=package,
        execution_receipt={
            "run_id": "run-provider-learning",
            "agent_id": "agent-1",
            "role_id": "role-1",
        },
    )

    assert len(output["experiences"]) == 2
    assert len(output["evaluations"]) == 2
    assert len(output["candidates"]) == 2

    assert all(
        item.promotion_status
        == "EXTERNAL_REVIEW_REQUIRED"
        for item in output["candidates"]
    )


def test_learning_service_invokes_pre_l5_guard(
    tmp_path,
):
    class SpyGuard:
        def __init__(self):
            self.before = 0
            self.after = 0
            self.learning = 0

        def validate_before(self, _request):
            self.before += 1

        def validate_after(self, _receipt):
            self.after += 1

        def validate_learning_outputs(
            self,
            *,
            candidates,
            mind_review,
        ):
            assert candidates
            assert mind_review
            self.learning += 1

    spy = SpyGuard()

    service = AgenticLearningService(
        project_root=tmp_path,
        source_commit_sha="2" * 40,
        pre_l5_guard=spy,
    )

    service.store = ExperienceStore(
        root=tmp_path / "experience"
    )

    req = request(tmp_path)

    fake_receipt = receipt()

    service.runtime = SimpleNamespace(
        execute=lambda _request: fake_receipt
    )

    package = WorkspaceStatePackage(
        state_package_id=STATE,
        project_id=PROJECT,
        task_id=TASK,
        repository=req.environment.repository,
        task_branch=req.environment.task_branch,
        base_sha=req.environment.base_sha,
        expected_head=req.environment.expected_head,
        authorization=req.authorization,
        authority_source="WORKSPACE_MANAGER",
    )

    result = service.execute_and_learn(
        package=package,
        request=req,
    )

    assert result["institutional_knowledge_promoted"] is False
    assert result["external_review_required"] is True

    assert spy.before == 1
    assert spy.after == 1
    assert spy.learning == 1