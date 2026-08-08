from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.operational_core_v1 import mount_operational_core_v1


IDENTITY = {
    "project_name": "PalWakf Local Agents",
    "domain": "agentic engineering platform",
    "target_audience": "Arabic-speaking engineering operator",
    "brand_personality": ["governed", "precise", "sovereign"],
    "visual_keywords": ["operations", "evidence", "calm"],
    "color_direction": "dark navy with restrained teal",
    "typography_direction": "Arabic-first high-legibility sans",
    "density": "balanced",
    "motion_level": "subtle",
    "accessibility_level": "enhanced",
    "text_direction": "rtl",
    "navigation_style": "operational sidebar with grouped sections",
    "card_style": "compact evidence cards",
    "corner_style": "moderate radius",
    "layout_signature": "cockpit summary above governed detail panels",
    "distinctive_traits": ["visible boundaries", "decision summaries"],
}


def make_client(tmp_path: Path) -> TestClient:
    (tmp_path / "frontend/src").mkdir(parents=True)
    (tmp_path / "frontend/src/App.tsx").write_text("export function App(){return null}\n", encoding="utf-8")
    app = FastAPI()
    mount_operational_core_v1(app, tmp_path)
    return TestClient(app)


def test_prepare_only_innovation_and_resilience(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepared_goal = client.post("/api/v1/operational-core/goal/prepare", json={"goal": "Build a resilient project cockpit"})
    assert prepared_goal.status_code == 200
    review = client.post("/api/v1/operational-core/innovation-reviews/prepare", json={
        "title": "Project cockpit",
        "context": "Create a clear operational cockpit without execution",
        "focus": "ux",
        "constraints": ["no model", "no execution"],
    })
    assert review.status_code == 200
    body = review.json()
    assert body["model_inference"] == "none"
    assert len(body["review"]["alternatives"]) == 3
    check = client.post("/api/v1/operational-core/resilience/context-check", json={"proposed_action": "Prepare a resilient project cockpit plan"})
    assert check.status_code == 200
    assert check.json()["automatic_action"] == "none"
    for _ in range(3):
        attempt = client.post("/api/v1/operational-core/resilience/attempts/register", json={"operation_key": "ui.cockpit", "fingerprint": "same-failure", "outcome": "failure"})
    assert attempt.json()["status"] == "ESCALATION_REQUIRED"
    checkpoint = client.post("/api/v1/operational-core/resilience/checkpoints", json={"label": "Before identity", "reason": "Preserve current planning metadata"})
    assert checkpoint.status_code == 200
    assert checkpoint.json()["snapshot_kind"] == "metadata_only"


def test_project_identity_and_similarity(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    first = client.put("/api/v1/operational-core/project-identities/palwakf-local-agents", json=IDENTITY)
    assert first.status_code == 200
    assert first.json()["execution_effect"] == "none"
    second_payload = dict(IDENTITY)
    second_payload["project_name"] = "Second Project"
    check = client.post("/api/v1/operational-core/project-identities/similarity-check", json={"project_key": "second-project", **second_payload})
    assert check.status_code == 200
    assert check.json()["similarity_score"] >= 70
    saved = client.put("/api/v1/operational-core/project-identities/second-project", json=second_payload)
    assert saved.status_code == 200
    assert saved.json()["identity"]["status"] == "prepared_only"
    dashboard = client.get("/api/v1/operational-core/innovation-resilience/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["boundaries"]["model_inference"] == "none"
