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
from palwakf_local_agents.agentic_core_v1.providers import ExecutionProvider, NativeProvider
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection
from palwakf_local_agents.agentic_core_v1.runtime import AgenticRuntime, AuthorityError

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
    assert h["operational_write_admission"] == "CLOSED_SEPARATE_GATE_REQUIRED"


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
            allowed_tools=["repository_manifest_read"],
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
            tool_policy=["repository_manifest_read"],
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


class FakeHermesProvider(ExecutionProvider):
    provider_id = ProviderId.HERMES

    def __init__(self):
        self.calls = 0

    def health(self):
        return {
            "provider_id": self.provider_id.value,
            "healthy": True,
            "adapter_modes": ["READ_ONLY_DIAGNOSTIC"],
            "operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
        }

    def execute_read_only(self, *, project_root: Path, request: RunRequest):
        self.calls += 1
        return {
            "provider_id": self.provider_id.value,
            "successful": True,
            "action_type": "HERMES_READ_ONLY_EXECUTION",
            "files": 3,
            "bytes": 128,
            "latency_ms": 12.5,
            "return_code": 0,
            "timed_out": False,
            "observations": [{"objective": request.objective}],
            "errors": [],
            "changed_files": [],
            "snapshot_changed_files": [],
            "evidence": [{"type": "HERMES_ADAPTER_EXECUTION_SUMMARY", "return_code": 0}],
        }


def make_hermes_request() -> RunRequest:
    req = make_request()
    req.provider_id = ProviderId.HERMES
    req.provider_mode = "READ_ONLY_DIAGNOSTIC"
    req.model_provider = "ollama"
    req.model_id = "llama3.2:3b"
    req.tools = ["read_file"]
    req.environment.tool_policy = ["read_file"]
    req.authorization.allowed_provider_ids = [ProviderId.HERMES]
    req.authorization.allowed_model_providers = ["ollama"]
    req.authorization.allowed_tools = ["read_file"]
    return req


def test_hermes_read_only_adapter_routes_through_execution_provider(monkeypatch):
    fake = FakeHermesProvider()
    req = make_hermes_request()
    monkeypatch.setenv(
        "PALWAKF_HERMES_CERTIFICATION_AUTHORIZATION_ID",
        req.authorization.authorization_id,
    )
    runtime = AgenticRuntime(
        root(),
        BASE,
        execution_providers={ProviderId.HERMES: fake, ProviderId.NATIVE: NativeProvider()},
    )
    receipt = runtime.execute(req)
    assert fake.calls == 1
    assert receipt.final_result == "PASS"
    assert receipt.provider_id == ProviderId.HERMES
    assert receipt.actions[0]["type"] == "HERMES_READ_ONLY_EXECUTION"
    assert "execute_via_hermes_adapter_read_only" in receipt.plan
    assert receipt.changed_files == []
    assert any(
        item.get("hermes_operational_write_admission") == "CLOSED_SEPARATE_GATE_REQUIRED"
        for item in receipt.observations
    )


def test_hermes_bounded_write_is_rejected_before_provider_execution():
    fake = FakeHermesProvider()
    req = make_hermes_request()
    req.authorization.read_only = False
    req.environment.filesystem_policy.mode = "BOUNDED_WRITE"
    runtime = AgenticRuntime(
        root(),
        BASE,
        execution_providers={ProviderId.HERMES: fake, ProviderId.NATIVE: NativeProvider()},
    )
    with pytest.raises(AuthorityError, match="WRITE_REQUIRES_SEPARATE_AUTHORITY"):
        runtime.execute(req)
    assert fake.calls == 0


def test_hermes_requires_explicit_ollama_model_route():
    fake = FakeHermesProvider()
    req = make_hermes_request()
    req.model_provider = "none"
    req.model_id = None
    req.authorization.allowed_model_providers = ["none"]
    runtime = AgenticRuntime(
        root(),
        BASE,
        execution_providers={ProviderId.HERMES: fake, ProviderId.NATIVE: NativeProvider()},
    )
    with pytest.raises(AuthorityError, match="HERMES_ADAPTER_REQUIRES_OLLAMA_MODEL"):
        runtime.execute(req)
    assert fake.calls == 0



def test_hermes_operational_admission_closed_without_run_bound_certification():
    fake = FakeHermesProvider()
    req = make_hermes_request()
    runtime = AgenticRuntime(
        root(),
        BASE,
        execution_providers={ProviderId.HERMES: fake, ProviderId.NATIVE: NativeProvider()},
    )
    with pytest.raises(AuthorityError, match="HERMES_OPERATIONAL_ADMISSION_CLOSED"):
        runtime.execute(req)
    assert fake.calls == 0


def test_request_tool_must_match_environment_tool_policy():
    req = make_request()
    req.environment.tool_policy = []
    with pytest.raises(AuthorityError, match="TOOL_POLICY_REQUEST_MISMATCH"):
        AgenticRuntime(root(), BASE).execute(req)


def test_request_tool_must_be_explicitly_authorized():
    req = make_request()
    req.authorization.allowed_tools = []
    with pytest.raises(AuthorityError, match="TOOL_NOT_AUTHORIZED"):
        AgenticRuntime(root(), BASE).execute(req)


def test_filesystem_roots_must_match_external_authority(tmp_path):
    req = make_request()
    narrower = tmp_path.resolve()
    req.environment.filesystem_policy.allowed_roots = [str(narrower)]
    with pytest.raises(AuthorityError, match="FILESYSTEM_ROOT_AUTHORITY_MISMATCH"):
        AgenticRuntime(root(), BASE).execute(req)


def test_hermes_certification_only_allows_read_file(monkeypatch):
    fake = FakeHermesProvider()
    req = make_hermes_request()
    req.tools = ["write_file"]
    req.environment.tool_policy = ["write_file"]
    req.authorization.allowed_tools = ["write_file"]
    monkeypatch.setenv(
        "PALWAKF_HERMES_CERTIFICATION_AUTHORIZATION_ID",
        req.authorization.authorization_id,
    )
    runtime = AgenticRuntime(
        root(),
        BASE,
        execution_providers={ProviderId.HERMES: fake, ProviderId.NATIVE: NativeProvider()},
    )
    with pytest.raises(
        AuthorityError,
        match="HERMES_CERTIFICATION_TOOL_POLICY_MUST_BE_READ_FILE_ONLY",
    ):
        runtime.execute(req)
    assert fake.calls == 0
