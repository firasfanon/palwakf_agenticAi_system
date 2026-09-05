from pathlib import Path

from palwakf_local_agents.agentic_core_v1.four_system_l4 import (
    AgenticL4Journal,
    FourSystemL4AgenticService,
    FourSystemL4ExecutionRequest,
)
from palwakf_local_agents.agentic_core_v1.intersystem_v1 import (
    AgenticIntegrationPilotResultV1,
    LearningCandidateBundleV1,
    WorkspaceAuthorityPackageV1,
)

HEAD = "2" * 40
BASE = "1" * 40


def package() -> WorkspaceAuthorityPackageV1:
    return WorkspaceAuthorityPackageV1(
        state_package_id="workspace-state-run-1",
        execution_run_id="run-1",
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="task-1",
        repository="firasfanon/palwakf_agenticAi_system",
        task_branch="task/example",
        base_sha=BASE,
        expected_head=HEAD,
        authority_reference="AUTH:test",
        objective="Read-only diagnostic",
        constraints=["NO_MUTATION"],
        timeout_seconds=60,
        scope_patterns=["backend/**"],
        required_capabilities=["READ_ONLY_DIAGNOSTIC"],
        required_tests=["L4"],
    )


def fake_result() -> AgenticIntegrationPilotResultV1:
    return AgenticIntegrationPilotResultV1(
        execution={
            "run_id": "agentic-run-1",
            "project_id": "PALWAKF_LOCAL_AGENTS",
            "task_id": "task-1",
            "state_package_id": "workspace-state-run-1",
            "changed_files": [],
            "final_result": "PASS",
        },
        experience={"experience_id": "exp-1"},
        evaluation={"evaluation_id": "eval-1", "run_id": "agentic-run-1", "passed": True},
        learning_bundle=LearningCandidateBundleV1(
            project_id="PALWAKF_LOCAL_AGENTS",
            task_id="task-1",
            run_id="agentic-run-1",
            source_sha=HEAD,
            candidates=(),
        ),
    )


def test_l4_agentic_execution_is_durable_and_idempotent(tmp_path: Path):
    calls = 0

    def executor(_):
        nonlocal calls
        calls += 1
        return fake_result()

    journal = AgenticL4Journal(tmp_path)
    service = FourSystemL4AgenticService(journal=journal, executor=executor)
    request = FourSystemL4ExecutionRequest(
        workspace_run_id="l4-run-1",
        correlation_id="corr-1",
        authority_package=package(),
    )

    first = service.execute(request)
    second = service.execute(request)

    assert first == second
    assert calls == 1
    assert first.agentic_result.institutional_knowledge_promoted is False
    assert first.agentic_result.external_review_required is True

    resumed = FourSystemL4AgenticService(
        journal=AgenticL4Journal(tmp_path),
        executor=executor,
    ).resume("l4-run-1")
    assert resumed.status == "COMPLETED"
    assert resumed.result is not None


def test_l4_agentic_replay_conflict_fails_closed(tmp_path: Path):
    service = FourSystemL4AgenticService(
        journal=AgenticL4Journal(tmp_path),
        executor=lambda _: fake_result(),
    )
    service.execute(
        FourSystemL4ExecutionRequest(
            workspace_run_id="l4-run-1",
            correlation_id="corr-1",
            authority_package=package(),
        )
    )

    try:
        service.execute(
            FourSystemL4ExecutionRequest(
                workspace_run_id="l4-run-1",
                correlation_id="corr-2",
                authority_package=package(),
            )
        )
    except ValueError as error:
        assert "IDEMPOTENCY_CONFLICT" in str(error)
    else:
        raise AssertionError("conflicting replay must fail closed")
