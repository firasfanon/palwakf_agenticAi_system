from pathlib import Path

import pytest
from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    ResourceBudget,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.registry_projection import (
    build_projection,
)
from palwakf_local_agents.agentic_core_v1.runtime import (
    AgenticRuntime,
    AuthorityError,
    RunControl,
)

BASE = "54ebb033287bbfb8b60d891be830c20a724e602f"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def make_request(
    *,
    timeout_seconds: int = 60,
    max_retries: int = 0,
    max_files: int = 8,
) -> RunRequest:
    agent = build_projection(root(), BASE)[0]
    authorization = AuthorizationEnvelope(
        authorization_id="AUTH-L5-RELIABILITY-001",
        issuer="HUMAN_EXPLICIT",
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="AGENTIC-L5-RUNTIME-RELIABILITY",
        allowed_agent_ids=[agent.agent_id],
        allowed_task_classes=["READ_ONLY_DIAGNOSTIC"],
        allowed_provider_ids=[ProviderId.NATIVE],
        allowed_model_providers=["none"],
        allowed_filesystem_roots=[str(root())],
        allowed_path_patterns=["backend/**"],
        read_only=True,
    )
    return RunRequest(
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="AGENTIC-L5-RUNTIME-RELIABILITY",
        state_package_id="STATE-L5-RELIABILITY-001",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class="READ_ONLY_DIAGNOSTIC",
        objective="Prove bounded runtime recovery controls.",
        provider_id=ProviderId.NATIVE,
        model_provider="none",
        authorization=authorization,
        environment=ExecutionEnvironment(
            project_id="PALWAKF_LOCAL_AGENTS",
            repository="firasfanon/palwakf_agenticAi_system",
            task_branch="task/AGENTIC-L5-ONE-MEGA-BATCH-V1",
            base_sha=BASE,
            expected_head=BASE,
            worktree=str(root()),
            filesystem_policy=FilesystemPolicy(
                mode="READ_ONLY",
                allowed_roots=[str(root())],
                allowed_patterns=["backend/**"],
            ),
            network_policy=NetworkPolicy(read=False, write=False),
            resource_budget=ResourceBudget(
                timeout_seconds=timeout_seconds,
                max_files=max_files,
                max_bytes=2_000_000,
                max_retries=max_retries,
            ),
        ),
    )


def checkpoint_path(receipt) -> Path:
    matches = [
        item["path"]
        for item in receipt.evidence
        if item["type"] == "RUN_CHECKPOINT_JSON"
    ]
    assert len(matches) == 1
    path = Path(matches[0])
    assert path.is_file()
    return path


def test_timeout_checkpoint_then_same_binding_resume_passes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(tmp_path))
    ticks = iter([0.0, 2.0])
    runtime = AgenticRuntime(
        root(),
        BASE,
        clock=lambda: next(ticks, 2.0),
    )
    request = make_request(timeout_seconds=1)

    timed_out = runtime.execute(request)

    assert timed_out.final_result == "TIMED_OUT"
    assert timed_out.errors[0]["code"] == "RUN_TIMEOUT"
    checkpoint = checkpoint_path(timed_out)

    resumed = AgenticRuntime(
        root(),
        BASE,
        clock=lambda: 0.0,
    ).execute(request, resume_checkpoint=checkpoint)

    assert resumed.final_result == "PASS"
    assert resumed.changed_files == []
    assert any(
        item.get("resume_from_run_id") == timed_out.run_id
        for item in resumed.observations
    )


def test_cancel_checkpoint_then_resume_passes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(tmp_path))
    runtime = AgenticRuntime(root(), BASE)
    request = make_request()
    control = RunControl()
    original_stat = runtime._stat_file
    calls = 0

    def cancel_after_first_stat(path: Path):
        nonlocal calls
        result = original_stat(path)
        calls += 1
        if calls == 1:
            control.cancel("OPERATOR_CANCEL_TEST")
        return result

    monkeypatch.setattr(runtime, "_stat_file", cancel_after_first_stat)
    cancelled = runtime.execute(request, control=control)

    assert cancelled.final_result == "CANCELLED"
    assert cancelled.errors[0] == {
        "code": "RUN_CANCELLED",
        "message": "OPERATOR_CANCEL_TEST",
    }
    checkpoint = checkpoint_path(cancelled)
    resumed = AgenticRuntime(root(), BASE).execute(
        request,
        resume_checkpoint=checkpoint,
    )
    assert resumed.final_result == "PASS"


def test_transient_file_stat_is_retried_within_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(tmp_path))
    runtime = AgenticRuntime(root(), BASE)
    request = make_request(max_retries=1)
    original_stat = runtime._stat_file
    failed_once = False

    def transient_once(path: Path):
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise OSError("TRANSIENT_TEST_ERROR")
        return original_stat(path)

    monkeypatch.setattr(runtime, "_stat_file", transient_once)
    receipt = runtime.execute(request)

    assert receipt.final_result == "PASS"
    assert receipt.retries == 1
    assert receipt.changed_files == []


def test_retry_exhaustion_is_fail_closed_and_resumable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(tmp_path))
    runtime = AgenticRuntime(root(), BASE)
    request = make_request(max_retries=1)

    def always_fails(_path: Path):
        raise OSError("PERSISTENT_TEST_ERROR")
    monkeypatch.setattr(runtime, "_stat_file", always_fails)
    receipt = runtime.execute(request)

    assert receipt.final_result == "FAILED_RETRYABLE"
    assert receipt.errors[0]["code"] == "FILE_STAT_RETRY_EXHAUSTED"
    assert receipt.retries == 1
    checkpoint_path(receipt)


def test_resume_rejects_any_request_binding_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(tmp_path))
    request = make_request()
    control = RunControl()
    control.cancel()
    checkpoint = checkpoint_path(
        AgenticRuntime(root(), BASE).execute(
            request,
            control=control,
        )
    )
    changed = request.model_copy(
        update={"objective": "Changed objective must not inherit checkpoint."}
    )

    with pytest.raises(AuthorityError, match="RESUME_BINDING_MISMATCH"):
        AgenticRuntime(root(), BASE).execute(
            changed,
            resume_checkpoint=checkpoint,
        )


def test_resume_rejects_checkpoint_outside_evidence_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setenv("PALWAKF_AGENTIC_EVIDENCE_ROOT", str(evidence))
    outside = tmp_path / "outside.checkpoint.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(
        AuthorityError,
        match="RESUME_CHECKPOINT_OUTSIDE_EVIDENCE_ROOT",
    ):
        AgenticRuntime(root(), BASE).execute(
            make_request(),
            resume_checkpoint=outside,
        )


def test_retry_budget_is_strictly_bounded() -> None:
    with pytest.raises(ValueError):
        ResourceBudget(max_retries=4)
