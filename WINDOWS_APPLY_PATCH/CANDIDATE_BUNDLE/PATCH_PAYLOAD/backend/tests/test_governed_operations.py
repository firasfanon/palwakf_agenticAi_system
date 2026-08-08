from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.governed_operations import mount_governed_operations
from palwakf_local_agents.workspace_core import mount_workspace_core

BASE = "/api/v1/governed-operations/workspaces/palwakf_government"


def make_client(project_root: Path) -> TestClient:
    app = FastAPI()
    mount_workspace_core(app, project_root)
    mount_governed_operations(app, project_root)
    return TestClient(app)


def _headers(base: dict[str, str], idempotency_key: str | None = None) -> dict[str, str]:
    result = dict(base)
    if idempotency_key:
        result["Idempotency-Key"] = idempotency_key
    return result


def make_task(client: TestClient, headers: dict[str, str]) -> dict:
    body = {
        "title": "مهمة اختبار محكومة محلية",
        "request": "اختبار دورة الحياة والمراجعة البشرية والأدلة محليًا فقط.",
        "system_scope": "local_agents",
        "risk_level": "medium",
        "requested_by": "test_operator",
        "requested_roles": [],
        "allowed_paths": [],
        "forbidden_actions": ["model_execution"],
        "evidence_required": ["source_verification"],
    }
    response = client.post(f"{BASE}/tasks", json=body, headers=_headers(headers, "test-idempotency-key-0001"))
    assert response.status_code == 201
    return response.json()["task"]


def transition(client: TestClient, headers: dict[str, str], task_id: str, version: int, path: str) -> dict:
    response = client.post(
        f"{BASE}/tasks/{task_id}/{path}",
        json={
            "actor_id": "test_operator",
            "rationale": "اختبار انتقال محكوم ضمن بيئة محلية فقط.",
            "evidence_ids": [],
            "expected_version": version,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["task"]


def test_operations_health_uses_per_workspace_local_sqlite_only(authorized_project: Path) -> None:
    with make_client(authorized_project) as client:
        body = client.get("/api/v1/governed-operations/health").json()
    assert body["workspace_scope_required"] == "YES"
    assert body["storage"] == "PER_WORKSPACE_LOCAL_SQLITE_ON_EXPLICIT_HUMAN_ACTION"
    assert body["model_execution"] == "NONE"
    assert body["pilot_execution"] == "NOT_EXECUTED"


def test_idempotent_create_returns_same_draft(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        first = make_task(client, governed_headers)
        body = {
            "title": "مهمة اختبار محكومة محلية",
            "request": "اختبار دورة الحياة والمراجعة البشرية والأدلة محليًا فقط.",
            "system_scope": "local_agents",
            "risk_level": "medium",
            "requested_by": "test_operator",
            "requested_roles": [],
            "allowed_paths": [],
            "forbidden_actions": ["model_execution"],
            "evidence_required": ["source_verification"],
        }
        replay = client.post(f"{BASE}/tasks", json=body, headers=_headers(governed_headers, "test-idempotency-key-0001"))
    assert replay.status_code == 201
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["task"]["task_id"] == first["task_id"]


def test_approval_is_blocked_until_required_evidence_exists(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        task = make_task(client, governed_headers)
        task = transition(client, governed_headers, task["task_id"], task["version"], "submit")
        task = transition(client, governed_headers, task["task_id"], task["version"], "start-review")
        rejected = client.post(
            f"{BASE}/tasks/{task['task_id']}/review",
            json={
                "actor_id": "test_operator",
                "rationale": "قرار اعتماد بشري محلي يحتاج الدليل المطلوب.",
                "evidence_ids": [],
                "expected_version": task["version"],
                "decision": "approve",
                "reviewer_attestation": "LOCAL_HUMAN_REVIEW_ASSERTED",
            },
            headers=governed_headers,
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == "APPROVAL_EVIDENCE_GATE_BLOCKED"
        evidence = client.post(
            f"{BASE}/evidence",
            json={
                "actor_id": "test_operator",
                "task_id": task["task_id"],
                "category": "source_verification",
                "source_type": "local_test",
                "trust_level": "verified",
                "raw_status": "verified",
                "summary": "دليل اختبار محلي",
                "source_reference": "local://test",
                "metadata": {},
            },
            headers=governed_headers,
        )
        assert evidence.status_code == 201
        approved = client.post(
            f"{BASE}/tasks/{task['task_id']}/review",
            json={
                "actor_id": "test_operator",
                "rationale": "اعتماد بشري محلي بعد اكتمال الدليل المطلوب.",
                "evidence_ids": [evidence.json()["evidence"]["evidence_id"]],
                "expected_version": task["version"],
                "decision": "approve",
                "reviewer_attestation": "LOCAL_HUMAN_REVIEW_ASSERTED",
            },
            headers=governed_headers,
        )
    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "approved"
    assert approved.json()["task"]["execution_state"] == "NOT_EXECUTED"


def test_version_conflict_is_rejected(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        task = make_task(client, governed_headers)
        conflict = client.post(
            f"{BASE}/tasks/{task['task_id']}/submit",
            json={
                "actor_id": "test_operator",
                "rationale": "محاولة انتقال بإصدار قديم عمدًا لاختبار الحماية.",
                "evidence_ids": [],
                "expected_version": 99,
            },
            headers=governed_headers,
        )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "TASK_VERSION_CONFLICT"


def test_hash_chain_integrity_and_no_execution_route(authorized_project: Path, governed_headers: dict[str, str]) -> None:
    with make_client(authorized_project) as client:
        task = make_task(client, governed_headers)
        bundle = client.get(f"{BASE}/tasks/{task['task_id']}")
        integrity = client.get(f"{BASE}/integrity")
        execute = client.post("/api/v1/governed-operations/execute")
        dispatch = client.post("/api/v1/governed-operations/dispatch")
    assert bundle.status_code == 200
    assert bundle.json()["integrity"]["integrity"] == "PASS"
    assert integrity.json()["audit_chain_integrity"] == "PASS"
    assert execute.status_code == 404
    assert dispatch.status_code == 404
