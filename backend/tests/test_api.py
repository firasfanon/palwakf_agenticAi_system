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
