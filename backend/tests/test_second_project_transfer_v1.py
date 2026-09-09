from __future__ import annotations

from pathlib import Path

import pytest

from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.intersystem_v1 import (
    WorkspaceAuthorityPackageV1,
    execute_integration_pilot,
)
from palwakf_local_agents.agentic_core_v1.learning_service import AgenticLearningService
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError

RUNTIME_SOURCE_SHA = "61bf483949d84f3cf380ee9c44937d0cbf5c73db"
TARGET_HEAD = "2" * 40
TARGET_PROJECT_ID = "SECOND_PROJECT_TRANSFER_FIXTURE"
TARGET_TASK_ID = "SECOND_PROJECT_TRANSFER_READ_ONLY_PROOF_V1"
TARGET_REPOSITORY = "example/second-project"
TARGET_BRANCH = "task/SECOND-PROJECT-TRANSFER-PROOF-V1"


def _runtime_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _package(*, expected_head: str = TARGET_HEAD, repository: str = TARGET_REPOSITORY):
    return WorkspaceAuthorityPackageV1(
        state_package_id="state-second-project-transfer-v1",
        execution_run_id="run-second-project-transfer-v1",
        project_id=TARGET_PROJECT_ID,
        task_id=TARGET_TASK_ID,
        repository=repository,
        task_branch=TARGET_BRANCH,
        base_sha="1" * 40,
        expected_head=expected_head,
        authority_reference="WORKSPACE_SECOND_PROJECT_TRANSFER_R1",
        objective="Prove read-only execution against a target project distinct from the Agentic runtime source.",
        constraints=["READ_ONLY", "NO_AUTHORITY_EXPANSION"],
        timeout_seconds=60,
        scope_patterns=["**"],
        read_only=True,
        allow_network_read=False,
        allow_network_write=False,
        required_capabilities=[],
        required_tests=["SECOND_PROJECT_TRANSFER_READ_ONLY_PROOF"],
        requested_provider_id="PALWAKF_NATIVE_AGENT",
        requested_model_provider="none",
    )


def test_second_project_transfer_uses_runtime_agents_and_target_manifest(tmp_path):
    runtime_root = _runtime_root()
    target_root = tmp_path / "second-project"
    target_root.mkdir()
    (target_root / "target_only.txt").write_text("SECOND_PROJECT_TARGET", encoding="utf-8")

    assert target_root.resolve() != runtime_root.resolve()
    assert not (target_root / "agents" / "registry_v2.yaml").exists()

    learning = AgenticLearningService(
        project_root=runtime_root,
        source_commit_sha=RUNTIME_SOURCE_SHA,
    )
    result = execute_integration_pilot(
        learning=learning,
        package=_package(),
        project_root=runtime_root,
        source_commit_sha=RUNTIME_SOURCE_SHA,
        target_project_root=target_root,
        target_expected_head=TARGET_HEAD,
    )

    execution = result.execution
    assert execution["final_result"] == "PASS"
    assert execution["before_head"] == TARGET_HEAD
    assert Path(execution["environment"]["worktree"]).resolve() == target_root.resolve()
    assert execution["environment"]["project_id"] == TARGET_PROJECT_ID
    assert result.learning_bundle.source_sha == TARGET_HEAD

    manifest = execution["observations"][0]["manifest_sample"]
    assert any(item["path"] == "target_only.txt" for item in manifest)
    assert all(item["path"] != "agents/registry_v2.yaml" for item in manifest)
    assert execution["changed_files"] == []


def test_second_project_transfer_rejects_unverified_target_head(tmp_path):
    target_root = tmp_path / "second-project"
    target_root.mkdir()
    learning = AgenticLearningService(
        project_root=_runtime_root(),
        source_commit_sha=RUNTIME_SOURCE_SHA,
    )

    with pytest.raises(ValueError, match="INTERSYSTEM_EXPECTED_HEAD_SOURCE_MISMATCH"):
        execute_integration_pilot(
            learning=learning,
            package=_package(expected_head=TARGET_HEAD),
            project_root=_runtime_root(),
            source_commit_sha=RUNTIME_SOURCE_SHA,
            target_project_root=target_root,
            target_expected_head="3" * 40,
        )


def test_target_authorized_root_cannot_escape_target_project(tmp_path):
    runtime_root = _runtime_root()
    target_root = tmp_path / "second-project"
    target_root.mkdir()
    agent = next(a for a in build_projection(runtime_root, RUNTIME_SOURCE_SHA) if a.runnable)
    task_class = agent.allowed_task_classes[0]

    auth = AuthorizationEnvelope(
        authorization_id="auth-second-project-negative",
        issuer="WORKSPACE_MANAGER",
        project_id=TARGET_PROJECT_ID,
        task_id=TARGET_TASK_ID,
        allowed_agent_ids=[agent.agent_id],
        allowed_task_classes=[task_class],
        allowed_provider_ids=[ProviderId.NATIVE],
        allowed_model_providers=["none"],
        allowed_filesystem_roots=[str(runtime_root)],
        allowed_path_patterns=["**"],
        read_only=True,
        allow_network_read=False,
        allow_network_write=False,
    )
    env = ExecutionEnvironment(
        project_id=TARGET_PROJECT_ID,
        repository=TARGET_REPOSITORY,
        task_branch=TARGET_BRANCH,
        base_sha="1" * 40,
        expected_head=TARGET_HEAD,
        worktree=str(target_root),
        filesystem_policy=FilesystemPolicy(
            mode="READ_ONLY",
            allowed_roots=[str(runtime_root)],
            allowed_patterns=["**"],
        ),
        network_policy=NetworkPolicy(read=False, write=False),
        tool_policy=[],
    )
    request = RunRequest(
        project_id=TARGET_PROJECT_ID,
        task_id=TARGET_TASK_ID,
        state_package_id="state-second-project-negative",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class=task_class,
        objective="Reject an authorized root outside the target project.",
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        skill_ids=[],
        tools=[],
        authorization=auth,
        environment=env,
    )

    runtime = AgenticRuntime(
        runtime_root,
        RUNTIME_SOURCE_SHA,
        target_project_root=target_root,
        target_expected_head=TARGET_HEAD,
    )
    with pytest.raises(AuthorityError, match="AUTHORIZED_ROOT_OUTSIDE_PROJECT"):
        runtime.execute(request)


def test_same_project_legacy_defaults_remain_backward_compatible():
    root = _runtime_root()
    learning = AgenticLearningService(
        project_root=root,
        source_commit_sha=RUNTIME_SOURCE_SHA,
    )
    package = WorkspaceAuthorityPackageV1(
        state_package_id="state-same-project-legacy",
        execution_run_id="run-same-project-legacy",
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="LEGACY_SAME_PROJECT_COMPATIBILITY_V1",
        repository="firasfanon/palwakf_agenticAi_system",
        task_branch="task/LEGACY-SAME-PROJECT-COMPATIBILITY-V1",
        base_sha="1" * 40,
        expected_head=RUNTIME_SOURCE_SHA,
        authority_reference="WORKSPACE_LEGACY_COMPATIBILITY",
        objective="Verify same-project defaults remain compatible.",
        constraints=["READ_ONLY"],
        timeout_seconds=60,
        scope_patterns=["backend/**"],
        read_only=True,
        allow_network_read=False,
        allow_network_write=False,
        required_capabilities=[],
        required_tests=["LEGACY_COMPATIBILITY"],
        requested_provider_id="PALWAKF_NATIVE_AGENT",
        requested_model_provider="none",
    )

    result = execute_integration_pilot(
        learning=learning,
        package=package,
        project_root=root,
        source_commit_sha=RUNTIME_SOURCE_SHA,
    )
    assert result.execution["final_result"] == "PASS"
    assert Path(result.execution["environment"]["worktree"]).resolve() == root.resolve()
    assert result.execution["before_head"] == RUNTIME_SOURCE_SHA
