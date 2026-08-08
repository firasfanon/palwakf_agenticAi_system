from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.operational_core_v1 import mount_operational_core_v1
from palwakf_local_agents.operational_core_v1.state_store import GovernedLocalStateStore


def test_state_store_and_vertical_slice(tmp_path: Path) -> None:
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/App.tsx").write_text("export function App(){return null}\n", encoding="utf-8")
    (tmp_path / "backend/src/palwakf_local_agents").mkdir(parents=True)
    (tmp_path / "backend/src/palwakf_local_agents/sample.py").write_text("from fastapi import APIRouter\nrouter=APIRouter()\n@router.get('/x')\ndef x(): return {}\n", encoding="utf-8")
    store = GovernedLocalStateStore(tmp_path)
    state = store.prepare_goal({"goal": "Build a safe local console", "project_type": "full_stack", "target_user": "developer", "priority": "normal", "constraints": []})
    assert state["revision"] == 1
    assert len(state["tasks"]) == 6
    assert store.list_events(10)[-1]["event_type"] == "goal.prepared"


def test_router_contract(tmp_path: Path) -> None:
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/App.tsx").write_text("export function App(){return null}\n", encoding="utf-8")
    app = FastAPI()
    mount_operational_core_v1(app, tmp_path)
    client = TestClient(app)
    assert client.get("/api/v1/operational-core/health").status_code == 200
    prepared = client.post("/api/v1/operational-core/goal/prepare", json={"goal": "Build one vertical slice"})
    assert prepared.status_code == 200
    body = prepared.json()
    assert body["execution_authority"] == "none"
    task_id = body["state"]["tasks"][0]["task_id"]
    transitioned = client.post(f"/api/v1/operational-core/tasks/{task_id}/transition", json={"action": "ready_for_review"})
    assert transitioned.status_code == 200
    assert client.get("/api/v1/operational-core/codebase-index").status_code == 200
    tools = client.get("/api/v1/operational-core/tools").json()
    assert tools["runtime"] == "governed_read_only"
    readiness = client.get("/api/v1/operational-core/model-readiness").json()
    assert readiness["no_model_invocation"] is True
