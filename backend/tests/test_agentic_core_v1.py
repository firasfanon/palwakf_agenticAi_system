from pathlib import Path
import pytest

from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope, ExecutionEnvironment, FilesystemPolicy,
    NetworkPolicy, ProviderId, RunRequest
)
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError
from palwakf_local_agents.agentic_core_v1.providers import NativeProvider

BASE = "8c1280413ecc6d45a9991dcb059279be14c330e3"

def root() -> Path:
    return Path(__file__).resolve().parents[2]

def test_projection_has_14_mapped_agents():
    agents = build_projection(root(), BASE)
    assert len(agents) == 14
    assert all(a.runnable for a in agents)

def test_native_provider_is_read_only():
    h = NativeProvider().health()
    assert h["healthy"] is True
    assert h["filesystem_policy"] == "READ_ONLY_BY_DEFAULT"

def make_request(project_id="PALWAKF_LOCAL_AGENTS"):
    a = build_projection(root(), BASE)[0]
    return RunRequest(
        project_id=project_id,
        task_id="TASK-MEGA-A-001",
        state_package_id="STATE-MEGA-A-001",
        agent_id=a.agent_id,
        role_id=a.role_id,
        task_class="READ_ONLY_DIAGNOSTIC",
        objective="Read-only repository diagnostic.",
        provider_id=ProviderId.NATIVE,
        model_provider="none",
        skill_ids=[],
        tools=["repository_manifest_read"],
        authorization=AuthorizationEnvelope(
            authorization_id="AUTH-MEGA-A-001",
            issuer="HUMAN_EXPLICIT",
            project_id="PALWAKF_LOCAL_AGENTS",
            task_id="TASK-MEGA-A-001",
            allowed_agent_ids=[a.agent_id],
            allowed_task_classes=["READ_ONLY_DIAGNOSTIC"],
            allowed_provider_ids=[ProviderId.NATIVE],
            allowed_model_providers=["none"],
            read_only=True,
            allowed_filesystem_roots=[str(root())],
        ),
        environment=ExecutionEnvironment(
            project_id=project_id,
            repository="firasfanon/palwakf_agenticAi_system",
            task_branch="task/AGENTIC_CORE_RUNTIME_AND_PROVIDER_CONVERGENCE_V1",
            base_sha=BASE,
            expected_head=BASE,
            worktree=str(root()),
            filesystem_policy=FilesystemPolicy(mode="READ_ONLY", allowed_roots=[str(root())]),
            network_policy=NetworkPolicy(read=False, write=False),
        ),
    )

def test_real_native_read_only_run_emits_receipt():
    receipt = AgenticRuntime(root(), BASE).execute(make_request())
    assert receipt.final_result == "PASS"
    assert receipt.changed_files == []
    assert receipt.actions[0]["type"] == "READ_ONLY_REPOSITORY_MANIFEST"
    assert receipt.evidence

def test_cross_project_denied():
    with pytest.raises(AuthorityError, match="CROSS_PROJECT_ACCESS_DENIED"):
        AgenticRuntime(root(), BASE).execute(make_request("OTHER_PROJECT"))

def test_skill_expansion_denied():
    req = make_request()
    req.skill_ids = ["unauthorized_skill"]
    with pytest.raises(AuthorityError, match="SKILL_SCOPE_EXPANSION_DENIED"):
        AgenticRuntime(root(), BASE).execute(req)
