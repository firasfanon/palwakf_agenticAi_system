from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.governed_operations import mount_governed_operations
from palwakf_local_agents.workspace_core import mount_workspace_core

BASE = "/api/v1/governed-operations/workspaces/palwakf_government"


def _client(project_root: Path) -> TestClient:
    app = FastAPI()
    mount_workspace_core(app, project_root)
    mount_governed_operations(app, project_root)
    return TestClient(app)


def _task_payload() -> dict:
    return {
        "title": "مهمة محكومة ضمن مساحة العمل للاختبار",
        "request": "إعداد مسودة تحقق من الدليل مع بقاء النموذج والتنفيذ معطلين بالكامل.",
        "system_scope": "local_agents",
        "risk_level": "medium",
        "requested_by": "test_operator",
        "requested_roles": ["coordinator"],
        "allowed_paths": [],
        "forbidden_actions": ["model_execution"],
        "evidence_required": ["source_verification"],
    }


def _transition(version: int) -> dict:
    return {
        "actor_id": "test_operator",
        "rationale": "اختبار انتقال محلي محكوم ضمن مساحة عمل واحدة.",
        "evidence_ids": [],
        "expected_version": version,
    }


def _headers(base: dict[str, str], idempotency_key: str | None = None) -> dict[str, str]:
    result = dict(base)
    if idempotency_key:
        result["Idempotency-Key"] = idempotency_key
    return result


def test_workspace_scope_is_required_and_legacy_writes_are_not_exposed(authorized_project: Path) -> None:
    with _client(authorized_project) as client:
        health = client.get("/api/v1/governed-operations/health")
        unscoped = client.post("/api/v1/governed-operations/tasks", json=_task_payload())
        execute = client.post("/api/v1/governed-operations/execute")
    assert health.status_code == 200
    assert health.json()["workspace_scope_required"] == "YES"
    assert unscoped.status_code == 404
    assert execute.status_code == 404


def test_task_is_physically_scoped_and_cross_workspace_read_is_rejected(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with _client(authorized_project) as client:
        first = client.post(f"{BASE}/tasks", json=_task_payload(), headers=_headers(governed_headers, "gov-scope-task-0001"))
        assert first.status_code == 201
        task_id = first.json()["task"]["task_id"]
        wrong = client.get(f"/api/v1/governed-operations/workspaces/personal_development/tasks/{task_id}")
        correct = client.get(f"{BASE}/tasks/{task_id}")
    assert wrong.status_code == 404
    assert wrong.json()["detail"]["code"] == "WORKSPACE_GOVERNED_TASK_NOT_FOUND"
    assert correct.status_code == 200
    assert correct.json()["task"]["workspace_id"] == "palwakf_government"


def test_foreign_workspace_injection_is_rejected_before_workspace_store_creation(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with _client(authorized_project) as client:
        rejected = client.post(
            f"{BASE}/tasks",
            json={**_task_payload(), "workspace_id": "personal_development"},
            headers=_headers(governed_headers, "foreign-scope-0001"),
        )
    assert rejected.status_code == 422
    assert not (authorized_project / "workspaces" / "personal_development" / "governed_operations.sqlite").exists()


def test_policy_intersection_and_approval_still_do_not_execute(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with _client(authorized_project) as client:
        created = client.post(f"{BASE}/tasks", json=_task_payload(), headers=_headers(governed_headers, "policy-scope-0001"))
        assert created.status_code == 201
        task = created.json()["task"]
        assert task["permission_intersection"]["model_execution"] == "NONE"
        task = client.post(f"{BASE}/tasks/{task['task_id']}/submit", json=_transition(task["version"]), headers=governed_headers).json()["task"]
        task = client.post(f"{BASE}/tasks/{task['task_id']}/start-review", json=_transition(task["version"]), headers=governed_headers).json()["task"]
        blocked = client.post(
            f"{BASE}/tasks/{task['task_id']}/review",
            json={**_transition(task["version"]), "decision": "approve", "reviewer_attestation": "LOCAL_HUMAN_REVIEW_ASSERTED"},
            headers=governed_headers,
        )
        assert blocked.status_code == 409
        evidence = client.post(
            f"{BASE}/evidence",
            json={
                "task_id": task["task_id"],
                "actor_id": "test_operator",
                "category": "source_verification",
                "source_type": "local_test",
                "trust_level": "verified",
                "raw_status": "verified",
                "summary": "دليل محلي للاختبار",
                "source_reference": "local://test",
                "metadata": {},
            },
            headers=governed_headers,
        )
        assert evidence.status_code == 201
        approved = client.post(
            f"{BASE}/tasks/{task['task_id']}/review",
            json={
                **_transition(task["version"]),
                "evidence_ids": [evidence.json()["evidence"]["evidence_id"]],
                "decision": "approve",
                "reviewer_attestation": "LOCAL_HUMAN_REVIEW_ASSERTED",
            },
            headers=governed_headers,
        )
    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "approved"
    assert approved.json()["task"]["execution_state"] == "NOT_EXECUTED"
