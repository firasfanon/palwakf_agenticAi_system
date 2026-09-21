from fastapi.testclient import TestClient
from palwakf_local_agents.app import app


def test_health_is_local_and_safe():
    with TestClient(app) as client:
        response = client.get('/health')
    assert response.status_code == 200
    body = response.json()
    assert body['bind_scope'] == '127.0.0.1_only'
    assert body['agent_execution_enabled'] is False
    assert body['platform_mutation_enabled'] is False
    assert body['database_access_enabled'] is False
    assert body['safety_ok'] is True


def test_agents_are_registered():
    with TestClient(app) as client:
        response = client.get('/api/agents')
    assert response.status_code == 200
    ids = {row['id'] for row in response.json()}
    assert {'coordinator', 'sovereignty_reviewer', 'tester', 'coding_builder'} <= ids


def test_run_is_explicitly_disabled():
    with TestClient(app) as client:
        response = client.post('/api/tasks/TASK-EXAMPLE/run')
    assert response.status_code == 403
    assert response.json()['detail']['code'] == 'AGENT_EXECUTION_DISABLED'


def test_agentic_health_uses_live_source_commit_sha(monkeypatch):
    import subprocess
    from pathlib import Path

    from palwakf_local_agents.app import create_app

    monkeypatch.delenv("PALWAKF_SOURCE_COMMIT_SHA", raising=False)
    project_root = Path(__file__).resolve().parents[2]
    expected = subprocess.check_output(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    with TestClient(create_app(project_root)) as client:
        response = client.get("/api/v1/agentic/health")

    assert response.status_code == 200
    assert response.json()["source_commit_sha"] == expected


def test_invalid_explicit_source_commit_sha_fails_closed(monkeypatch):
    from pathlib import Path

    import pytest
    from palwakf_local_agents.app import create_app

    monkeypatch.setenv("PALWAKF_SOURCE_COMMIT_SHA", "not-a-valid-sha")
    project_root = Path(__file__).resolve().parents[2]

    with pytest.raises(RuntimeError, match="PALWAKF_SOURCE_COMMIT_SHA_INVALID"):
        create_app(project_root)


def test_non_git_runtime_root_uses_source_repository_head(tmp_path, monkeypatch):
    import subprocess
    from pathlib import Path

    from palwakf_local_agents.app import _resolve_source_commit_sha

    monkeypatch.delenv("PALWAKF_SOURCE_COMMIT_SHA", raising=False)
    source_root = Path(__file__).resolve().parents[2]
    expected = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()

    assert _resolve_source_commit_sha(tmp_path) == expected
