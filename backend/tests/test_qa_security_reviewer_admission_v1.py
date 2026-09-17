from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    IndependentReviewSpec,
    NetworkPolicy,
    ProviderId,
    ReviewEvidenceRecord,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError

SOURCE_SHA = "06e80fd487b6ff98dc9fb978017be4c0f6c5a3bc"
ADMISSION = "PREL5-025"


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def make_repo(tmp_path: Path, *, risky: bool = False) -> tuple[Path, str, str]:
    repo = tmp_path / "review-target"
    (repo / "src").mkdir(parents=True)
    _git(repo.parent, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "PALWAKF Test")
    (repo / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "src/app.py")
    _git(repo, "commit", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    content = "value = 2\n"
    if risky:
        content += "result = eval('1+1')\n"
    (repo / "src" / "app.py").write_text(content, encoding="utf-8")
    _git(repo, "add", "src/app.py")
    _git(repo, "commit", "-m", "change")
    head = _git(repo, "rev-parse", "HEAD")
    return repo, base, head


def evidence(head: str, status: str = "PASS") -> list[ReviewEvidenceRecord]:
    kinds = ["TARGETED_TESTS", "FULL_REGRESSION", "REMOTE_READBACK"]
    return [
        ReviewEvidenceRecord(
            evidence_id=f"ev-{index}",
            evidence_type=kind,
            status=status,
            source_head_sha=head,
            detail_sha256=hashlib.sha256(f"{kind}:{head}".encode()).hexdigest(),
        )
        for index, kind in enumerate(kinds)
    ]


def make_request(repo: Path, base: str, head: str) -> RunRequest:
    agent = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "qa_security_reviewer_agentic_v1"
    )
    required = ["TARGETED_TESTS", "FULL_REGRESSION", "REMOTE_READBACK"]
    spec = IndependentReviewSpec(
        base_sha=base,
        head_sha=head,
        expected_changed_files=["src/app.py"],
        allowed_path_patterns=["src/**"],
        required_evidence_types=required,
        evidence=evidence(head),
    )
    return RunRequest(
        project_id="REVIEW_TARGET",
        task_id="PREL5-025-PILOT",
        state_package_id="PREL5-025-STATE",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class="INDEPENDENT_QA_SECURITY_REVIEW",
        objective="Review exact governed change without mutation.",
        provider_id=ProviderId.NATIVE,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="none",
        skill_ids=["qa_security_review", "evidence_assessment"],
        tools=["deterministic_qa_security_review"],
        review_spec=spec,
        authorization=AuthorizationEnvelope(
            authorization_id="AUTH-PREL5-025-PILOT",
            issuer="WORKSPACE_MANAGER",
            project_id="REVIEW_TARGET",
            task_id="PREL5-025-PILOT",
            allowed_agent_ids=[agent.agent_id],
            allowed_task_classes=["INDEPENDENT_QA_SECURITY_REVIEW"],
            allowed_provider_ids=[ProviderId.NATIVE],
            allowed_model_providers=["none"],
            allowed_tools=["deterministic_qa_security_review"],
            allowed_filesystem_roots=[str(repo)],
            allowed_path_patterns=["src/**"],
            read_only=True,
            agent_admission_reference=ADMISSION,
        ),
        environment=ExecutionEnvironment(
            project_id="REVIEW_TARGET",
            repository="firasfanon/review-target",
            task_branch="task/PREL5-025-PILOT",
            base_sha=base,
            expected_head=head,
            worktree=str(repo),
            filesystem_policy=FilesystemPolicy(
                mode="READ_ONLY",
                allowed_roots=[str(repo)],
                allowed_patterns=["src/**"],
            ),
            network_policy=NetworkPolicy(read=False, write=False),
            tool_policy=["deterministic_qa_security_review"],
            db_authority="NONE",
        ),
    )


def runtime_for(repo: Path, head: str) -> AgenticRuntime:
    return AgenticRuntime(
        source_root(),
        SOURCE_SHA,
        target_project_root=repo,
        target_expected_head=head,
    )


def test_projection_requires_external_admission_for_qa_reviewer() -> None:
    agent = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "qa_security_reviewer_agentic_v1"
    )
    assert agent.required_admission_reference == ADMISSION
    assert "INDEPENDENT_QA_SECURITY_REVIEW" in agent.allowed_task_classes
    assert agent.tool_bindings == ["deterministic_qa_security_review"]
    assert agent.filesystem_scope == "READ_ONLY_BY_DEFAULT"


def test_independent_review_pilot_passes_without_mutation(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    before = _git(repo, "status", "--porcelain")
    receipt = runtime_for(repo, head).execute(make_request(repo, base, head))
    after = _git(repo, "status", "--porcelain")

    assert receipt.final_result == "PASS"
    assert receipt.changed_files == []
    assert before == after == ""
    action = receipt.actions[0]
    assert action["type"] == "INDEPENDENT_QA_SECURITY_REVIEW"
    assert all(action["review_dimensions"].values())
    assert action["findings"] == []


def test_high_risk_diff_fails_closed(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path, risky=True)
    receipt = runtime_for(repo, head).execute(make_request(repo, base, head))

    assert receipt.final_result == "FAIL_CLOSED"
    assert receipt.changed_files == []
    action = receipt.actions[0]
    assert action["review_dimensions"]["security_review"] is False
    assert any(item["type"] == "DYNAMIC_EVAL" for item in action["findings"])


def test_wrong_admission_reference_is_denied(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    request = make_request(repo, base, head)
    request.authorization.agent_admission_reference = "PREL5-999"
    with pytest.raises(AuthorityError, match="ADMISSION_REFERENCE_MISMATCH"):
        runtime_for(repo, head).execute(request)


def test_network_database_or_write_authority_is_denied(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    request = make_request(repo, base, head)
    request.authorization.allow_network_read = True
    with pytest.raises(AuthorityError, match="INDEPENDENT_REVIEW_NETWORK_DENIED"):
        runtime_for(repo, head).execute(request)

    request = make_request(repo, base, head)
    request.environment.db_authority = "READ_ONLY"
    with pytest.raises(AuthorityError, match="INDEPENDENT_REVIEW_DATABASE_DENIED"):
        runtime_for(repo, head).execute(request)

    request = make_request(repo, base, head)
    request.authorization.read_only = False
    with pytest.raises(AuthorityError, match="BOUNDED_WRITE_AUTHORITY_MODE_MISMATCH"):
        runtime_for(repo, head).execute(request)


def test_scope_and_evidence_binding_fail_closed(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    request = make_request(repo, base, head)
    request.review_spec.expected_changed_files = ["src/other.py"]
    receipt = runtime_for(repo, head).execute(request)
    assert receipt.final_result == "FAIL_CLOSED"
    assert any(
        item.get("code") == "CHANGED_FILES_MISMATCH"
        for item in receipt.errors
    )

    request = make_request(repo, base, head)
    request.review_spec.evidence[0].source_head_sha = base
    receipt = runtime_for(repo, head).execute(request)
    assert receipt.final_result == "FAIL_CLOSED"
    assert any(
        item.get("code") == "EVIDENCE_HEAD_MISMATCH"
        for item in receipt.errors
    )


def test_model_inference_and_hermes_are_denied(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    request = make_request(repo, base, head)
    request.model_provider = "ollama"
    request.model_id = "local-model"
    with pytest.raises(AuthorityError, match="MODEL_PROVIDER_NOT_AUTHORIZED"):
        runtime_for(repo, head).execute(request)

    request = make_request(repo, base, head)
    request.provider_id = ProviderId.HERMES
    request.authorization.allowed_provider_ids = [ProviderId.HERMES]
    with pytest.raises(AuthorityError, match="HERMES_ADAPTER_REQUIRES_OLLAMA_MODEL"):
        runtime_for(repo, head).execute(request)


def test_non_qa_agent_cannot_use_review_path(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    request = make_request(repo, base, head)
    other = next(
        item
        for item in build_projection(source_root(), SOURCE_SHA)
        if item.agent_id == "coding_builder_agentic_v1"
    )
    request.agent_id = other.agent_id
    request.role_id = other.role_id
    request.authorization.allowed_agent_ids = [other.agent_id]
    with pytest.raises(AuthorityError, match="AGENT_TASK_CLASS_NOT_ALLOWED"):
        runtime_for(repo, head).execute(request)
