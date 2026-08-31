from __future__ import annotations

from pathlib import Path

import pytest

from palwakf_local_agents.agentic_core_v1.contracts import AuthorizationEnvelope, ExecutionEnvironment, FilesystemPolicy, NetworkPolicy, ProviderId, RunRequest
from palwakf_local_agents.agentic_core_v1.external_contracts import ExternalContractAdapter, WorkspaceStatePackage
from palwakf_local_agents.agentic_core_v1.learning_service import AgenticLearningService
from palwakf_local_agents.agentic_core_v1.orchestration import MultiAgentOrchestrator
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection

BASE_SHA = "1807b450f17904d17cfbe418ded7d61ee5029b56"
PROJECT_ID = "PALWAKF_LOCAL_AGENTS"
TASK_ID = "AGENTIC_LEARNING_MULTI_AGENT_AND_END_TO_END_INTEGRATION_V1"
BRANCH = "task/AGENTIC_LEARNING_MULTI_AGENT_AND_END_TO_END_INTEGRATION_V1"

def _root() -> Path:
    return Path(__file__).resolve().parents[2]

def _fixture():
    root = _root()
    agent = next(a for a in build_projection(root, BASE_SHA) if a.runnable)
    task_class = agent.allowed_task_classes[0]
    auth = AuthorizationEnvelope(authorization_id="auth-b-e2e", issuer="WORKSPACE_MANAGER", project_id=PROJECT_ID, task_id=TASK_ID, allowed_agent_ids=[agent.agent_id], allowed_task_classes=[task_class], allowed_provider_ids=[ProviderId.NATIVE, ProviderId.HERMES], allowed_model_providers=["none", "ollama"], allowed_filesystem_roots=[str(root)], read_only=True, allow_network_read=True, allow_network_write=False)
    env = ExecutionEnvironment(project_id=PROJECT_ID, repository="firasfanon/palwakf_agenticAi_system", task_branch=BRANCH, base_sha=BASE_SHA, expected_head=BASE_SHA, worktree=str(root), filesystem_policy=FilesystemPolicy(mode="READ_ONLY", allowed_roots=[str(root)]), network_policy=NetworkPolicy(read=True, write=False), tool_policy=[])
    package = WorkspaceStatePackage(state_package_id="state-b-e2e", project_id=PROJECT_ID, task_id=TASK_ID, repository="firasfanon/palwakf_agenticAi_system", task_branch=BRANCH, base_sha=BASE_SHA, expected_head=BASE_SHA, authorization=auth, authority_source="WORKSPACE_MANAGER")
    request = RunRequest(project_id=PROJECT_ID, task_id=TASK_ID, state_package_id=package.state_package_id, agent_id=agent.agent_id, role_id=agent.role_id, task_class=task_class, objective="Perform a governed read-only diagnostic and derive a learning candidate.", provider_id=ProviderId.NATIVE, provider_mode="READ_ONLY_DIAGNOSTIC", model_provider="none", skill_ids=[], tools=[], authorization=auth, environment=env)
    return root, package, request

def test_execute_and_learn_under_external_authority():
    root, package, request = _fixture()
    result = AgenticLearningService(project_root=root, source_commit_sha=BASE_SHA).execute_and_learn(package=package, request=request)
    assert result["receipt"]["final_result"] == "PASS"
    assert result["evaluation"]["passed"] is True
    assert len(result["learning_candidates"]) == 1
    assert result["institutional_knowledge_promoted"] is False
    assert result["external_review_required"] is True
    assert result["mind_submission"]["auto_promotion"] is False

def test_cross_project_learning_fails_closed():
    _, package, _ = _fixture()
    payload = package.model_dump()
    payload["project_id"] = "OTHER_PROJECT"
    with pytest.raises(ValueError, match="STATE_PACKAGE_PROJECT_AUTHORITY_MISMATCH"):
        WorkspaceStatePackage.model_validate(payload)

def test_mind_submission_cannot_auto_promote():
    root, package, request = _fixture()
    result = AgenticLearningService(project_root=root, source_commit_sha=BASE_SHA).execute_and_learn(package=package, request=request)
    assert result["mind_review"]["accepted_project_knowledge"] is False
    assert result["mind_review"]["review_mode"] == "CANDIDATE_ONLY_NO_AUTO_PROMOTION"
    assert result["mind_submission"]["knowledge_authority"] == "EXTERNAL_MIND_WORKSPACE_REVIEW"

def test_provider_policy_is_replaceable_under_external_envelope():
    _, package, _ = _fixture()
    policy = MultiAgentOrchestrator().provider_policy(package)
    assert policy["replaceable"] is True
    assert "PALWAKF_NATIVE_AGENT" in policy["execution_providers"]
    assert "HERMES_AGENT" in policy["execution_providers"]
    assert "ollama" in policy["model_providers"]

def test_delegate_cannot_expand_authority():
    _, package, request = _fixture()
    bad = request.model_copy(update={"agent_id": "not-authorized-agent", "objective": "attempt authority expansion"})
    with pytest.raises(ValueError, match="DELEGATION_AGENT_AUTHORITY_EXPANSION_DENIED"):
        MultiAgentOrchestrator().plan(package=package, primary=request, delegates=[bad])

def test_external_adapter_rejects_head_mismatch():
    _, package, _ = _fixture()
    payload = package.model_dump()
    payload["expected_head"] = "0" * 40
    bad = WorkspaceStatePackage.model_validate(payload)
    with pytest.raises(ValueError, match="WORKSPACE_HEAD_BINDING_MISMATCH"):
        ExternalContractAdapter().validate_workspace_package(bad)
