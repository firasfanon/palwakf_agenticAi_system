from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.workspace_core import mount_workspace_core


def make_client(tmp_path: Path) -> TestClient:
    app = FastAPI()
    mount_workspace_core(app, tmp_path)
    return TestClient(app)


def test_builtin_workspaces_are_declared_and_isolated(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        health = client.get("/api/v1/workspaces/health")
        items = client.get("/api/v1/workspaces")
    assert health.status_code == 200
    assert health.json()["workspace_count"] == 4
    assert health.json()["cross_workspace_access"] == "REJECTED_BY_CONTRACT"
    ids = {item["workspace_id"] for item in items.json()["items"]}
    assert ids == {"palwakf_government", "personal_development", "commercial_projects", "research_learning"}
    assert not (tmp_path / "workspaces" / "palwakf_government" / "state.sqlite").exists()


def test_policies_do_not_transfer_government_constraints(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        government = client.get("/api/v1/workspaces/palwakf_government/policy").json()
        developer = client.get("/api/v1/workspaces/personal_development/policy").json()
    assert government["execution"]["model_execution"] == "NONE"
    assert developer["execution"]["model_execution"] == "NONE_BY_DEFAULT"
    assert government["tools"]["platform_bridge"] == "EXPLICIT_GATE_ONLY"
    assert developer["tools"]["platform_bridge"] == "NOT_CONFIGURED"


def test_cross_workspace_and_path_traversal_are_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        traversal = client.get("/api/v1/workspaces/../palwakf_government")
        unknown = client.get("/api/v1/workspaces/not-a-real-workspace")
    assert traversal.status_code in {404, 400}
    assert unknown.status_code == 404


def test_policy_and_audit_integrity_are_workspace_scoped(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        integrity = client.get("/api/v1/workspaces/palwakf_government/audit-integrity")
        readiness = client.get("/api/v1/workspaces/palwakf_government/readiness")
    assert integrity.status_code == 200
    assert integrity.json()["audit_chain_integrity"] == "PASS"
    assert readiness.json()["workspace_storage_initialized"] is False
    assert readiness.json()["next_authorized_step"] == "WORKSPACE_STORAGE_AND_OPERATIONS_BINDING_REQUIRES_SEPARATE_APPROVAL"


def test_no_execution_or_create_workspace_route_exists(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        execute = client.post("/api/v1/workspaces/palwakf_government/execute")
        create = client.post("/api/v1/workspaces")
    assert execute.status_code == 404
    assert create.status_code == 405

def test_workspace_ui_uses_arabic_operational_labels_and_overflow_safe_styles() -> None:
    static_root = Path(__file__).resolve().parents[1] / "src" / "palwakf_local_agents" / "workspace_core" / "static"
    index = (static_root / "index.html").read_text(encoding="utf-8")
    styles = (static_root / "styles.css").read_text(encoding="utf-8")
    script = (static_root / "app.js").read_text(encoding="utf-8")
    assert 'lang="ar"' in index
    assert "مساحات العمل والسياسات" in index
    assert "LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1" in index
    assert "const labels=" in script
    assert "function format(" in script
    assert "tech-details" in script
    assert "JSON.stringify" in script
    assert "overflow-wrap:anywhere" in styles
    assert "white-space:pre-wrap" in styles
    assert "setInterval" not in script
    assert "setTimeout" not in script
