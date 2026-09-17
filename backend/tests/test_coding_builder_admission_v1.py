from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    BoundedFileMutation,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.providers import NativeProvider
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError

SOURCE_SHA = "197546f3811f064326910a0c3e1045b7843c41b4"
TARGET_SHA = "a" * 40
ADMISSION = "PREL5-024"


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
def make_request(target: Path, *, path: str = "src/demo.txt", content: str = "after\n") -> RunRequest:
    agent = next(
        item for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "coding_builder_agentic_v1"
    )
    target_file = target / Path(path)
    before = target_file.read_bytes() if target_file.is_file() else None
    before_sha = hashlib.sha256(before).hexdigest() if before is not None else "ABSENT"
    mutation = BoundedFileMutation(
        path=path,
        content=content,
        content_sha256=digest(content),
        expected_before_sha256=before_sha,
    )
    return RunRequest(
        project_id="PILOT_PROJECT",
        task_id="PREL5-024-PILOT",
        state_package_id="PREL5-024-STATE",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class="BOUNDED_SOURCE_MUTATION",
        objective="Apply one bounded source mutation.",
        provider_id=ProviderId.NATIVE,
        provider_mode="BOUNDED_WRITE",
        model_provider="none",        skill_ids=["patch_plan_generation"],
        tools=["bounded_file_write"],
        file_mutations=[mutation],
        authorization=AuthorizationEnvelope(
            authorization_id="AUTH-PREL5-024-PILOT",
            issuer="WORKSPACE_MANAGER",
            project_id="PILOT_PROJECT",
            task_id="PREL5-024-PILOT",
            allowed_agent_ids=[agent.agent_id],
            allowed_task_classes=["BOUNDED_SOURCE_MUTATION"],
            allowed_provider_ids=[ProviderId.NATIVE],
            allowed_model_providers=["none"],
            allowed_tools=["bounded_file_write"],
            allowed_filesystem_roots=[str(target)],
            allowed_path_patterns=["src/**"],
            read_only=False,
            agent_admission_reference=ADMISSION,
        ),
        environment=ExecutionEnvironment(
            project_id="PILOT_PROJECT",
            repository="firasfanon/pilot_project",
            task_branch="task/PREL5-024-PILOT",
            base_sha=TARGET_SHA,
            expected_head=TARGET_SHA,
            worktree=str(target),
            filesystem_policy=FilesystemPolicy(
                mode="BOUNDED_WRITE",
                allowed_roots=[str(target)],
                allowed_patterns=["src/**"],
            ),            network_policy=NetworkPolicy(read=False, write=False),
            tool_policy=["bounded_file_write"],
        ),
    )


def runtime_for(target: Path) -> AgenticRuntime:
    return AgenticRuntime(
        source_root(),
        SOURCE_SHA,
        target_project_root=target,
        target_expected_head=TARGET_SHA,
    )


def prepare_target(tmp_path: Path) -> Path:
    target = tmp_path / "target"
    (target / "src").mkdir(parents=True)
    return target


def test_projection_requires_external_admission_for_coding_builder() -> None:
    agent = next(
        item for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "coding_builder_agentic_v1"
    )
    assert agent.required_admission_reference == ADMISSION
    assert "BOUNDED_SOURCE_MUTATION" in agent.allowed_task_classes
    assert "bounded_file_write" in agent.tool_bindings


def test_bounded_write_pilot_mutates_only_authorized_file(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target, content="pilot-pass\n")
    receipt = runtime_for(target).execute(request)

    assert receipt.final_result == "PASS"
    assert receipt.changed_files == ["src/demo.txt"]
    assert (target / "src/demo.txt").read_text(encoding="utf-8") == "pilot-pass\n"
    assert receipt.actions[0]["type"] == "NATIVE_BOUNDED_FILE_MUTATION"
    assert "execute_native_bounded_file_mutation" in receipt.plan


def test_missing_admission_reference_fails_before_mutation(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.authorization.agent_admission_reference = None

    with pytest.raises(AuthorityError, match="ADMISSION_REFERENCE_MISMATCH"):
        runtime_for(target).execute(request)
    assert not (target / "src/demo.txt").exists()


def test_scope_escape_is_fail_closed(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target, path="../escape.txt")
    receipt = runtime_for(target).execute(request)

    assert receipt.final_result == "FAIL_CLOSED"
    assert receipt.changed_files == []
    assert not (tmp_path / "escape.txt").exists()

def test_preflight_failure_does_not_partially_mutate(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    first = target / "src/first.txt"
    second = target / "src/second.txt"
    first.write_text("before-first\n", encoding="utf-8")
    second.write_text("before-second\n", encoding="utf-8")

    request = make_request(target, path="src/first.txt", content="after-first\n")
    request.file_mutations.append(
        BoundedFileMutation(
            path="src/second.txt",
            content="after-second\n",
            content_sha256=digest("after-second\n"),
            expected_before_sha256="0" * 64,
        )
    )
    receipt = runtime_for(target).execute(request)

    assert receipt.final_result == "FAIL_CLOSED"
    assert first.read_text(encoding="utf-8") == "before-first\n"
    assert second.read_text(encoding="utf-8") == "before-second\n"
    assert receipt.changed_files == []


def test_non_builder_agent_cannot_use_bounded_write(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    tester = next(
        item for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "tester_agentic_v1"
    )
    request.agent_id = tester.agent_id
    request.role_id = tester.role_id
    request.authorization.allowed_agent_ids = [tester.agent_id]

    with pytest.raises(AuthorityError, match="AGENT_TASK_CLASS_NOT_ALLOWED"):
        runtime_for(target).execute(request)
    assert not (target / "src/demo.txt").exists()


def test_native_provider_direct_call_still_requires_admission(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.authorization.agent_admission_reference = None

    with pytest.raises(RuntimeError, match="ADMISSION_REFERENCE_REQUIRED"):
        NativeProvider().execute_bounded_write(project_root=target, request=request)
    assert not (target / "src/demo.txt").exists()


def test_network_or_database_authority_is_denied(tmp_path: Path) -> None:
    target = prepare_target(tmp_path)
    request = make_request(target)
    request.authorization.allow_network_read = True

    with pytest.raises(AuthorityError, match="BOUNDED_WRITE_NETWORK_DENIED"):
        runtime_for(target).execute(request)

    request = make_request(target)
    request.environment.db_authority = "READ_ONLY"
    with pytest.raises(AuthorityError, match="BOUNDED_WRITE_DATABASE_DENIED"):
        runtime_for(target).execute(request)
