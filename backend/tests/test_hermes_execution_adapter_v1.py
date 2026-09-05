from pathlib import Path
import json
import sqlite3
import shutil
import inspect
from types import SimpleNamespace

import yaml

from palwakf_local_agents.agentic_core_v1.contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunRequest,
)
from palwakf_local_agents.agentic_core_v1.providers import HermesProvider
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection

BASE = "8c1280413ecc6d45a9991dcb059279be14c330e3"


def root() -> Path:
    return Path(__file__).resolve().parents[2]




def write_tool_state(hermes_home: Path, tool_name: str) -> None:
    db_path = hermes_home / "state.db"
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("CREATE TABLE messages (tool_calls TEXT)")
        payload = [{"function": {"name": tool_name, "arguments": "{}"}}]
        connection.execute("INSERT INTO messages(tool_calls) VALUES (?)", (json.dumps(payload),))
        connection.commit()
    finally:
        connection.close()


def make_request() -> RunRequest:
    agent = build_projection(root(), BASE)[0]
    pattern = "backend/tests/test_agentic_core_v1.py"
    return RunRequest(
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="TASK-HERMES-ADAPTER-001",
        state_package_id="STATE-HERMES-ADAPTER-001",
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class="READ_ONLY_DIAGNOSTIC",
        objective="Read the authorized test file and summarize its safety assertions.",
        provider_id=ProviderId.HERMES,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider="ollama",
        model_id="llama3.2:3b",
        skill_ids=[],
        tools=["read_file"],
        authorization=AuthorizationEnvelope(
            authorization_id="AUTH-HERMES-ADAPTER-001",
            issuer="HUMAN_EXPLICIT",
            project_id="PALWAKF_LOCAL_AGENTS",
            task_id="TASK-HERMES-ADAPTER-001",
            allowed_agent_ids=[agent.agent_id],
            allowed_task_classes=["READ_ONLY_DIAGNOSTIC"],
            allowed_provider_ids=[ProviderId.HERMES],
            allowed_model_providers=["ollama"],
            allowed_tools=["read_file"],
            allowed_filesystem_roots=[str(root())],
            allowed_path_patterns=[pattern],
            read_only=True,
        ),
        environment=ExecutionEnvironment(
            project_id="PALWAKF_LOCAL_AGENTS",
            repository="firasfanon/palwakf_agenticAi_system",
            task_branch="task/AGENTIC_HERMES_EXECUTION_ADAPTER_INTEGRATION_V1",
            base_sha=BASE,
            expected_head=BASE,
            worktree=str(root()),
            filesystem_policy=FilesystemPolicy(
                mode="READ_ONLY",
                allowed_roots=[str(root())],
                allowed_patterns=[pattern],
            ),
            network_policy=NetworkPolicy(read=False, write=False),
            tool_policy=["read_file"],
        ),
    )


def test_hermes_adapter_builds_isolated_config_and_explicit_cwd(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )
    observed = {}

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        observed["command"] = command
        observed["cwd"] = Path(cwd)
        observed["terminal_cwd"] = Path(env["TERMINAL_CWD"])
        config_path = Path(env["HERMES_HOME"]) / "config.yaml"
        observed["config"] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        assert observed["cwd"] == Path(env["HERMES_HOME"])
        assert observed["cwd"] != observed["terminal_cwd"]
        assert observed["cwd"].name == "hermes-home"
        assert observed["terminal_cwd"].name == "workspace"
        assert (
            observed["terminal_cwd"] / "backend/tests/test_agentic_core_v1.py"
        ).is_file()
        return SimpleNamespace(returncode=0, stdout="READ_ONLY_OK", stderr="")

    monkeypatch.setattr("palwakf_local_agents.agentic_core_v1.providers.subprocess.run", fake_run)
    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is True
    assert result["snapshot_changed_files"] == []
    assert "--no-restore-cwd" in observed["command"]
    assert "--in" in observed["command"]
    assert observed["config"]["terminal"]["backend"] == "local"
    assert Path(observed["config"]["terminal"]["cwd"]) == observed["terminal_cwd"]
    assert observed["config"]["custom_providers"][0]["extra_body"]["tool_choice"] == "auto"
    assert observed["config"]["agent"]["tool_use_enforcement"] is True


def test_hermes_adapter_detects_snapshot_write_without_touching_source(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )
    source_rogue = root() / "rogue.txt"
    assert not source_rogue.exists()

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        Path(env["TERMINAL_CWD"], "rogue.txt").write_text(
            "unauthorized",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("palwakf_local_agents.agentic_core_v1.providers.subprocess.run", fake_run)
    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is False
    assert "rogue.txt" in result["snapshot_changed_files"]
    assert any(error["code"] == "HERMES_READ_ONLY_SNAPSHOT_MUTATION_DETECTED" for error in result["errors"])
    assert not source_rogue.exists()



def test_hermes_adapter_rejects_write_tool_call_even_on_disposable_snapshot(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        write_tool_state(Path(env["HERMES_HOME"]), "write_file")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("palwakf_local_agents.agentic_core_v1.providers.subprocess.run", fake_run)
    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is False
    assert result["unexpected_tools"] == ["write_file"]
    assert any(error["code"] == "HERMES_READ_ONLY_TOOL_POLICY_VIOLATION" for error in result["errors"])


def test_hermes_adapter_rejects_non_loopback_model_endpoint():
    try:
        HermesProvider._assert_loopback_ollama("https://example.com:11434")
    except RuntimeError as error:
        assert str(error) == "HERMES_MODEL_ENDPOINT_MUST_BE_LOOPBACK"
    else:
        raise AssertionError("non-loopback endpoint was not rejected")



def test_execution_provider_abstract_contract_remains_valid():
    from palwakf_local_agents.agentic_core_v1.providers import ExecutionProvider

    assert inspect.isabstract(ExecutionProvider)
    assert "health" in ExecutionProvider.__abstractmethods__
    assert "execute_read_only" in ExecutionProvider.__abstractmethods__
    assert "_cleanup_ephemeral_tree" not in ExecutionProvider.__dict__


def test_hermes_ephemeral_cleanup_retries_transient_windows_lock(monkeypatch, tmp_path):
    temp_root = tmp_path / "ephemeral"
    temp_root.mkdir()
    (temp_root / "state.db").write_text("x", encoding="utf-8")
    real_rmtree = shutil.rmtree
    attempts = {"count": 0}

    def flaky_rmtree(path):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError(32, "simulated transient Windows lock", str(path / "state.db"))
        return real_rmtree(path)

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.shutil.rmtree",
        flaky_rmtree,
    )
    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.time.sleep",
        lambda _: None,
    )

    ok, error, used = HermesProvider._cleanup_ephemeral_tree(
        temp_root,
        attempts=5,
        delay_seconds=0,
    )

    assert ok is True
    assert error is None
    assert used == 3
    assert attempts["count"] == 3
    assert not temp_root.exists()


def test_hermes_ephemeral_cleanup_failure_is_classified_fail_closed(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        return SimpleNamespace(returncode=0, stdout="READ_ONLY_OK", stderr="")

    def classified_cleanup(path, *, attempts=30, delay_seconds=0.2):
        shutil.rmtree(path)
        return False, "PermissionError: simulated persistent state.db lock", attempts

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.subprocess.run",
        fake_run,
    )
    monkeypatch.setattr(provider, "_cleanup_ephemeral_tree", classified_cleanup)

    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is False
    assert result["ephemeral_cleanup"] == "FAIL_CLOSED"
    assert any(
        error["code"] == "HERMES_EPHEMERAL_CLEANUP_FAILED"
        for error in result["errors"]
    )



def test_hermes_certification_profile_mismatch_fails_closed(monkeypatch):
    provider = HermesProvider()

    def wrong_version(command, *, capture_output, text, timeout, check):
        return SimpleNamespace(
            returncode=0,
            stdout="Hermes Agent v0.20.6 local deadbeef",
            stderr="",
        )

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.subprocess.run",
        wrong_version,
    )

    try:
        provider._assert_certified_profile("hermes")
    except RuntimeError as error:
        assert str(error) == "HERMES_CERTIFICATION_PROFILE_MISMATCH"
    else:
        raise AssertionError("uncertified Hermes profile was admitted")


def test_hermes_subprocess_environment_strips_secrets(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "MUST_NOT_LEAK")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "MUST_NOT_LEAK")
    observed = {}

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        observed["env"] = dict(env)
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        return SimpleNamespace(returncode=0, stdout="READ_ONLY_OK", stderr="")

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.subprocess.run",
        fake_run,
    )
    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is True
    assert "OPENAI_API_KEY" not in observed["env"]
    assert "SUPABASE_SERVICE_ROLE_KEY" not in observed["env"]
    assert observed["env"]["HERMES_HOME"]
    assert observed["env"]["TERMINAL_CWD"]
    assert observed["env"]["HOME"] == observed["env"]["HERMES_HOME"]
    assert observed["env"]["USERPROFILE"] == observed["env"]["HERMES_HOME"]


def test_authorized_files_honor_allowed_root(monkeypatch, tmp_path):
    from palwakf_local_agents.agentic_core_v1.providers import _authorized_files

    project = tmp_path / "project"
    allowed = project / "allowed"
    denied = project / "denied"
    allowed.mkdir(parents=True)
    denied.mkdir(parents=True)
    (allowed / "ok.txt").write_text("ok", encoding="utf-8")
    (denied / "no.txt").write_text("no", encoding="utf-8")

    request = make_request()
    request.environment.filesystem_policy.allowed_roots = [str(allowed)]
    request.environment.filesystem_policy.allowed_patterns = ["**/*.txt"]

    files, _ = _authorized_files(project, request)
    relative = [item[1] for item in files]

    assert relative == ["allowed/ok.txt"]



def test_hermes_process_cwd_is_isolated_from_file_tool_workspace(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )
    observed = {}

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        observed["cwd"] = Path(cwd)
        observed["terminal_cwd"] = Path(env["TERMINAL_CWD"])
        observed["hermes_home"] = Path(env["HERMES_HOME"])
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        return SimpleNamespace(returncode=0, stdout="READ_ONLY_OK", stderr="")

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.subprocess.run",
        fake_run,
    )

    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is True
    assert observed["cwd"] == observed["hermes_home"]
    assert observed["cwd"] != observed["terminal_cwd"]
    assert result["snapshot_changed_files"] == []
    assert result["observations"][0]["provider_process_cwd"] == str(observed["hermes_home"])
    assert result["observations"][0]["file_tool_workspace_cwd"] == str(observed["terminal_cwd"])



def test_provider_process_runtime_residue_is_not_snapshot_mutation(monkeypatch):
    provider = HermesProvider()
    monkeypatch.setattr(provider, "_executable", lambda: "hermes")
    monkeypatch.setattr(
        provider,
        "_assert_certified_profile",
        lambda exe: "Hermes Agent v0.20.5 local f4df86fe",
    )

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        write_tool_state(Path(env["HERMES_HOME"]), "read_file")
        Path(cwd, "provider-cache.db").write_text(
            "provider runtime residue",
            encoding="utf-8",
        )
        assert Path(cwd) == Path(env["HERMES_HOME"])
        assert Path(cwd) != Path(env["TERMINAL_CWD"])
        return SimpleNamespace(returncode=0, stdout="READ_ONLY_OK", stderr="")

    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.providers.subprocess.run",
        fake_run,
    )
    result = provider.execute_read_only(project_root=root(), request=make_request())

    assert result["successful"] is True
    assert result["snapshot_changed_files"] == []
    assert not any(
        error["code"] == "HERMES_READ_ONLY_SNAPSHOT_MUTATION_DETECTED"
        for error in result["errors"]
    )
