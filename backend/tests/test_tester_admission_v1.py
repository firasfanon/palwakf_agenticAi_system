from __future__ import annotations

from pathlib import Path

import pytest
from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ControlledTestSpec,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError

SOURCE_SHA = "4a55f0d4f0aa5084bce5fa2c44b7672d8e2b6964"
TARGET_SHA = "b" * 40
ADMISSION = "PREL5-026"


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def prepare_target(tmp_path: Path, *, failing: bool = False) -> Path:
    target = tmp_path / "disposable"
    tests = target / "tests"
    tests.mkdir(parents=True)
    body = "def test_value():\n    assert 2 + 2 == 4\n"
    if failing:
        body = "def test_value():\n    assert 2 + 2 == 5\n"
    (tests / "test_sample.py").write_text(body, encoding="utf-8")
    return target


def make_request(target: Path) -> RunRequest:
    agent = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "tester_agentic_v1"
    )
    return RunRequest(
        project_id="TEST_TARGET",
        task_id="PREL5-026-PILOT",
        state_package_id="PREL5-026-STATE",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class="CONTROLLED_TEST_EXECUTION",
        objective="Execute exact governed pytest selectors on a disposable copy.",
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        skill_ids=["test_plan_generation", "evidence_assessment"],
        tools=["controlled_pytest_execution"],
        test_spec=ControlledTestSpec(
            plan_id="PREL5-026-TEST-PLAN",
            selectors=["tests/test_sample.py"],
            expected_exit_code=0,
            timeout_seconds=30,
        ),
        authorization=AuthorizationEnvelope(
            authorization_id="AUTH-PREL5-026-PILOT",
            issuer="WORKSPACE_MANAGER",
            project_id="TEST_TARGET",
            task_id="PREL5-026-PILOT",
            allowed_agent_ids=[agent.agent_id],
            allowed_task_classes=["CONTROLLED_TEST_EXECUTION"],
            allowed_provider_ids=[ProviderId.NATIVE],
            allowed_model_providers=["none"],
            allowed_tools=["controlled_pytest_execution"],
            allowed_filesystem_roots=[str(target)],
            allowed_path_patterns=["tests/**"],
            read_only=True,
            agent_admission_reference=ADMISSION,
        ),
        environment=ExecutionEnvironment(
            project_id="TEST_TARGET",
            repository="firasfanon/test-target",
            task_branch="task/PREL5-026-PILOT",
            base_sha=TARGET_SHA,
            expected_head=TARGET_SHA,
            worktree=str(target),
            filesystem_policy=FilesystemPolicy(
                mode="READ_ONLY",
                allowed_roots=[str(target)],
                allowed_patterns=["tests/**"],
            ),
            network_policy=NetworkPolicy(read=False, write=False),
            tool_policy=["controlled_pytest_execution"],
            db_authority="NONE",
        ),
    )


def runtime_for(target: Path) -> AgenticRuntime:
    return AgenticRuntime(
        source_root(),
        SOURCE_SHA,
        target_project_root=target,
        target_expected_head=TARGET_SHA,
    )


def test_projection_requires_external_admission_for_tester() -> None:
    agent = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "tester_agentic_v1"
    )
    assert agent.required_admission_reference == ADMISSION
    assert "CONTROLLED_TEST_EXECUTION" in agent.allowed_task_classes
    assert agent.tool_bindings == ["controlled_pytest_execution"]
    assert agent.filesystem_scope == "READ_ONLY_BY_DEFAULT"


def test_controlled_pytest_pilot_passes_with_evidence(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    receipt = runtime_for(target).execute(make_request(target))

    assert receipt.final_result == "PASS"
    assert receipt.changed_files == []
    assert receipt.tests[0]["result"] == "PASS"
    assert receipt.actions[0]["type"] == "CONTROLLED_PYTEST_EXECUTION"
    assert receipt.actions[0]["test_plan"]["runner"] == "PYTHON_MODULE_PYTEST"
    assert receipt.evidence[0]["type"] == "CONTROLLED_TEST_EXECUTION_RECEIPT"


def test_failing_test_is_fail_closed_with_evidence(tmp_path: Path) -> None:
    target = prepare_target(tmp_path, failing=True)
    receipt = runtime_for(target).execute(make_request(target))

    assert receipt.final_result == "FAIL_CLOSED"
    assert receipt.tests[0]["result"] == "FAIL"
    assert any(
        item["code"] == "CONTROLLED_TEST_EXIT_MISMATCH" for item in receipt.errors
    )


def test_git_worktree_is_rejected(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    (target / ".git").mkdir()
    receipt = runtime_for(target).execute(make_request(target))
    assert receipt.final_result == "FAIL_CLOSED"
    assert any("DISPOSABLE_COPY_REQUIRED" in item["code"] for item in receipt.errors)


def test_selector_escape_is_rejected(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.test_spec.selectors = ["../test_escape.py"]
    receipt = runtime_for(target).execute(request)
    assert receipt.final_result == "FAIL_CLOSED"
    assert any("SELECTOR_INVALID" in item["code"] for item in receipt.errors)


def test_wrong_admission_and_external_authority_are_denied(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.authorization.agent_admission_reference = "PREL5-999"
    with pytest.raises(
        AuthorityError, match="CONTROLLED_TEST_ADMISSION_REFERENCE_MISMATCH"
    ):
        runtime_for(target).execute(request)

    request = make_request(target)
    request.authorization.allow_network_read = True
    with pytest.raises(
        AuthorityError, match="CONTROLLED_TEST_NETWORK_AUTHORITY_DENIED"
    ):
        runtime_for(target).execute(request)

    request = make_request(target)
    request.environment.db_authority = "READ_ONLY"
    with pytest.raises(AuthorityError, match="CONTROLLED_TEST_DATABASE_DENIED"):
        runtime_for(target).execute(request)


def test_model_hermes_and_non_tester_are_denied(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.model_provider = "ollama"
    request.model_id = "local-model"
    with pytest.raises(AuthorityError, match="MODEL_PROVIDER_NOT_AUTHORIZED"):
        runtime_for(target).execute(request)

    request = make_request(target)
    request.provider_id = ProviderId.HERMES
    request.authorization.allowed_provider_ids = [ProviderId.HERMES]
    with pytest.raises(AuthorityError):
        runtime_for(target).execute(request)

    request = make_request(target)
    other = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "qa_security_reviewer_agentic_v1"
    )
    request.agent_id = other.agent_id
    request.role_id = other.role_id
    request.authorization.allowed_agent_ids = [other.agent_id]
    with pytest.raises(AuthorityError, match="AGENT_TASK_CLASS_NOT_ALLOWED"):
        runtime_for(target).execute(request)
