from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.local_agent_core import mount_local_agent_core
from palwakf_local_agents.workspace_core import mount_workspace_core


def make_client(project_root: Path) -> TestClient:
    app = FastAPI()
    mount_workspace_core(app, project_root)
    mount_local_agent_core(app, project_root)
    return TestClient(app)


def payload(agent_id: str = "task_planning_runbook_agent_v1") -> dict:
    return {
        "agent_id": agent_id,
        "objective": "Prepare a governed local-agent foundation acceptance plan.",
        "requested_by": "local.operator",
        "requested_capabilities": ["mega_batch_plan", "uat_plan"],
        "source_summary": "MODEL_EXECUTION=NONE\nPILOT_EXECUTION=NOT_EXECUTED",
        "evidence_references": ["UAT-LOCAL-001"],
    }


def _headers(base: dict[str, str], idempotency_key: str) -> dict[str, str]:
    return {**base, "Idempotency-Key": idempotency_key}


def test_health_and_registry_are_workspace_scoped(authorized_project: Path) -> None:
    with make_client(authorized_project) as client:
        health = client.get("/api/v1/local-agent-core/health")
        assert health.status_code == 200
        assert health.json()["model_execution"] == "NONE"
        agents = client.get("/api/v1/local-agent-core/workspaces/palwakf_government/agents")
    assert agents.status_code == 200
    assert len(agents.json()["items"]) == 6


def test_prepare_is_local_deterministic_and_not_executed(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json=payload(),
            headers=_headers(local_agent_headers, "local-agent-core-test-001"),
        )
    assert response.status_code == 201
    item = response.json()["preparation"]
    assert item["execution_state"] == "NOT_EXECUTED"
    assert item["model_execution"] == "NONE"
    assert item["pilot_execution"] == "NOT_EXECUTED"
    assert item["preparation_state"] == "PREPARED_FOR_HUMAN_REVIEW"


def test_cross_workspace_preparation_read_is_denied(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        created = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json=payload(),
            headers=_headers(local_agent_headers, "local-agent-core-test-002"),
        ).json()["preparation"]
        other = client.get(
            f"/api/v1/local-agent-core/workspaces/personal_development/preparations/{created['preparation_id']}"
        )
    assert other.status_code == 404


def test_payload_workspace_injection_is_rejected(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    body = {**payload(), "workspace_id": "personal_development"}
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json=body,
            headers=_headers(local_agent_headers, "local-agent-core-test-003"),
        )
    assert response.status_code == 422


def test_prohibited_capability_is_denied(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    body = payload()
    body["requested_capabilities"] = ["shell_execution"]
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json=body,
            headers=_headers(local_agent_headers, "local-agent-core-test-004"),
        )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "LOCAL_AGENT_PREPARATION_DENIED"


def test_declared_not_activated_workspace_cannot_prepare(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/personal_development/preparations",
            json=payload(),
            headers=_headers(local_agent_headers, "local-agent-core-test-005"),
        )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "WORKSPACE_SCOPE_DENIED"


def test_unscoped_and_execute_routes_are_absent(authorized_project: Path) -> None:
    with make_client(authorized_project) as client:
        assert client.post("/api/v1/local-agent-core/preparations", json=payload()).status_code == 404
        assert client.post("/api/v1/local-agent-core/workspaces/palwakf_government/execute", json={}).status_code == 404


def test_integrity_and_memory_boundary(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json=payload(),
            headers=_headers(local_agent_headers, "local-agent-core-test-006"),
        )
        assert response.status_code == 201
        integrity = client.get("/api/v1/local-agent-core/workspaces/palwakf_government/integrity")
        memory = client.get("/api/v1/local-agent-core/workspaces/palwakf_government/memory-boundary")
    assert integrity.status_code == 200
    assert integrity.json()["audit_chain_integrity"] == "PASS"
    assert memory.json()["memory_write"] == "NONE"


def test_model_pilot_is_declared_but_disabled_by_default(authorized_project: Path) -> None:
    with make_client(authorized_project) as client:
        status = client.get("/api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/status")
    assert status.status_code == 200
    assert status.json()["pilot_enabled"] is False
    assert status.json()["external_network"] == "NONE"
    assert status.json()["decision"] == "DENY"


def test_model_pilot_draft_is_denied_without_explicit_enablement(authorized_project: Path, local_agent_headers: dict[str, str]) -> None:
    body = {
        "agent_id": "task_planning_runbook_agent_v1",
        "objective": "Prepare a local model pilot planning draft with mandatory human review.",
        "requested_by": "local.operator",
        "source_summary": "MODEL_EXECUTION=NONE",
        "evidence_references": ["PILOT-READINESS-001"],
    }
    with make_client(authorized_project) as client:
        response = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/drafts",
            json=body,
            headers=_headers(local_agent_headers, "model-pilot-disabled-001"),
        )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "MODEL_PILOT_DENIED"


def test_model_pilot_is_denied_for_other_workspace(authorized_project: Path) -> None:
    with make_client(authorized_project) as client:
        status = client.get("/api/v1/local-agent-core/workspaces/personal_development/model-pilot/status")
    assert status.status_code == 200
    assert status.json()["decision"] == "DENY"
