from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from palwakf_local_agents import store as legacy_store
from palwakf_local_agents.app import create_app


ROOT = Path(__file__).resolve().parents[2]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _actor(
    actor_id: str,
    token: str,
    workspace_scopes: list[str],
    allowed_actions: list[str],
    commercial_client_scopes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "token_sha256": _sha256(token),
        "workspace_scopes": workspace_scopes,
        "allowed_actions": allowed_actions,
        "commercial_client_scopes": commercial_client_scopes or [],
    }


def _snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return result


def _seed_project(tmp_path: Path, actors: list[dict[str, Any]]) -> None:
    shutil.copytree(ROOT / "policy_packs", tmp_path / "policy_packs")
    shutil.copytree(
        ROOT / "workspaces",
        tmp_path / "workspaces",
        ignore=shutil.ignore_patterns("*.sqlite", "*.sqlite-*", "*.sqlite3", "*.sqlite3-*"),
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "local_actor_scope_registry_v1.json").write_text(
        json.dumps(
            {
                "contract": "LOCAL_ACTOR_SCOPE_REGISTRY_V1",
                "version": "1.0",
                "default_access": "DENY",
                "actors": actors,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for filename in ("local_agent_model_pilot_v1.json", "controlled_first_prompt_pilot_v1.json"):
        shutil.copy2(ROOT / "config" / filename, tmp_path / "config" / filename)


def _client(tmp_path: Path, actors: list[dict[str, Any]]) -> TestClient:
    _seed_project(tmp_path, actors)
    legacy_store.PROJECT_ROOT = tmp_path
    legacy_store.DB_PATH = tmp_path / "audit" / "local_agents.sqlite"
    return TestClient(create_app(tmp_path))


def _global_task() -> dict[str, Any]:
    return {
        "title": "Legacy task disabled",
        "system_scope": "local_agents",
        "request": "This negative UAT proves that the unscoped legacy task route is disabled.",
        "risk_level": "medium",
        "allowed_paths": [],
        "forbidden_actions": ["model_execution"],
        "requested_roles": [],
        "evidence_required": [],
    }


def _governed_task(actor_id: str = "operator_a") -> dict[str, Any]:
    return {
        "title": "Negative authorization task",
        "request": "Verifies authorization rejection before a governed operations store mutation.",
        "system_scope": "local_agents",
        "risk_level": "medium",
        "requested_by": actor_id,
        "requested_roles": [],
        "allowed_paths": [],
        "forbidden_actions": ["model_execution"],
        "evidence_required": ["source_verification"],
    }


def _transition(actor_id: str = "operator_a") -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "rationale": "Authorization must reject this request before any mutation.",
        "evidence_ids": [],
        "expected_version": 1,
    }


def _review(actor_id: str = "operator_a") -> dict[str, Any]:
    return {**_transition(actor_id), "decision": "approve", "reviewer_attestation": "LOCAL_HUMAN_REVIEW_ASSERTED"}


def _evidence(actor_id: str = "operator_a") -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "category": "test",
        "source_type": "test",
        "trust_level": "verified",
        "raw_status": "verified",
        "summary": "negative authorization test",
        "source_reference": "local://negative",
    }


def _preparation(actor_id: str = "operator_a") -> dict[str, Any]:
    return {
        "agent_id": "task_planning_runbook_agent_v1",
        "objective": "Prepare a governed local agent negative UAT plan.",
        "requested_by": actor_id,
        "requested_capabilities": ["mega_batch_plan"],
        "source_summary": "MODEL_EXECUTION=NONE",
        "evidence_references": ["NEG-UAT-001"],
    }


def _pilot_draft(actor_id: str = "operator_a") -> dict[str, Any]:
    return {
        "agent_id": "task_planning_runbook_agent_v1",
        "objective": "Prepare a model pilot draft for negative UAT.",
        "requested_by": actor_id,
        "source_summary": "",
        "evidence_references": [],
    }


ALL_WRITE_ROUTES = (
    ("legacy_unscoped_task_disabled", "/api/tasks", _global_task(), {}, 410, "LEGACY_UNSCOPED_WRITE_ROUTE_DISABLED"),
    ("legacy_run_disabled", "/api/tasks/TASK-NONEXISTENT/run", {}, {}, 403, "AGENT_EXECUTION_DISABLED"),
    ("gcf_task_no_actor", "/api/v1/governed-capability-foundation/workspaces/palwakf_government/tasks", {"title": "x", "description": ""}, {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("gcf_project_no_actor", "/api/v1/governed-capability-foundation/workspaces/palwakf_government/projects", {"name": "x", "description": ""}, {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("gcf_review_no_actor", "/api/v1/governed-capability-foundation/workspaces/palwakf_government/reviews", {"subject_type": "task", "subject_id": "x", "decision": "approved"}, {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("gcf_tool_no_actor", "/api/v1/governed-capability-foundation/workspaces/palwakf_government/tools/summarize", {"text": "x"}, {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("gcf_pilot_no_actor", "/api/v1/governed-capability-foundation/pilot/execute", {"workspace_id": "research_learning", "prompt": "x", "human_reviewer": "operator_a", "explicit_execution_confirmation": False}, {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_create_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/tasks", _governed_task(), {"Idempotency-Key": "negative-0001"}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_submit_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/tasks/GWS-TEST/submit", _transition(), {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_start_review_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/tasks/GWS-TEST/start-review", _transition(), {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_review_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/tasks/GWS-TEST/review", _review(), {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_archive_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/tasks/GWS-TEST/archive", _transition(), {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("go_evidence_no_actor", "/api/v1/governed-operations/workspaces/palwakf_government/evidence", _evidence(), {}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("lac_preparation_no_actor", "/api/v1/local-agent-core/workspaces/palwakf_government/preparations", _preparation(), {"Idempotency-Key": "negative-0002"}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
    ("lac_pilot_draft_no_actor", "/api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/drafts", _pilot_draft(), {"Idempotency-Key": "negative-0003"}, 401, "AUTHENTICATED_ACTOR_REQUIRED"),
)


@pytest.mark.parametrize("name,path,payload,headers,status,code", ALL_WRITE_ROUTES)
def test_all_15_write_routes_reject_without_mutation(tmp_path: Path, name: str, path: str, payload: dict[str, Any], headers: dict[str, str], status: int, code: str) -> None:
    with _client(tmp_path, []) as client:
        before = _snapshot(tmp_path)
        response = client.post(path, json=payload, headers=headers)
        after = _snapshot(tmp_path)
    assert response.status_code == status, name
    assert response.json()["detail"]["code"] == code, name
    assert after == before, name


@pytest.mark.parametrize(
    "name,path,payload,headers,status,code",
    (
        ("invalid_bearer", "/api/v1/governed-operations/workspaces/palwakf_government/tasks", _governed_task(), {"Authorization": "Bearer invalid", "Idempotency-Key": "negative-invalid"}, 401, "ACTOR_AUTHENTICATION_FAILED"),
        ("wrong_workspace", "/api/v1/local-agent-core/workspaces/palwakf_government/preparations", _preparation(), {"Authorization": "Bearer research-token", "Idempotency-Key": "negative-workspace"}, 403, "WORKSPACE_SCOPE_DENIED"),
        ("wrong_action", "/api/v1/governed-operations/workspaces/palwakf_government/tasks", _governed_task(), {"Authorization": "Bearer read-token", "Idempotency-Key": "negative-action"}, 403, "WORKSPACE_ACTION_DENIED"),
        ("dotted_actor_identifier", "/api/v1/governed-operations/workspaces/palwakf_government/tasks", _governed_task("local.operator"), {"Authorization": "Bearer dotted-token", "Idempotency-Key": "negative-dotted"}, 403, "WORKSPACE_ACTION_DENIED"),
        ("declared_actor_spoof", "/api/v1/governed-operations/workspaces/palwakf_government/tasks", _governed_task("operator_b"), {"Authorization": "Bearer gov-token", "Idempotency-Key": "negative-spoof"}, 403, "DECLARED_ACTOR_MISMATCH"),
        ("commercial_client_mismatch", "/api/v1/governed-capability-foundation/workspaces/commercial_projects/tasks", {"title": "Client-safe task", "description": "Mismatched client must be denied before the store.", "client_id": "client_b"}, {"Authorization": "Bearer commercial-token"}, 403, "COMMERCIAL_CLIENT_SCOPE_DENIED"),
        ("commercial_client_missing", "/api/v1/governed-capability-foundation/workspaces/commercial_projects/tasks", {"title": "Client-safe task", "description": "Missing client must be denied before the store."}, {"Authorization": "Bearer commercial-token"}, 400, "COMMERCIAL_CLIENT_CONTEXT_REQUIRED"),
        ("commercial_client_conflict", "/api/v1/governed-capability-foundation/workspaces/commercial_projects/tasks", {"title": "Client-safe task", "description": "Conflicting client context must be denied before the store.", "client_id": "client_a"}, {"Authorization": "Bearer commercial-token", "X-Palwakf-Client-Id": "client_b"}, 400, "CLIENT_CONTEXT_CONFLICT"),
        ("commercial_legacy_blocked", "/api/v1/governed-operations/workspaces/commercial_projects/tasks", _governed_task(), {"Authorization": "Bearer commercial-token", "Idempotency-Key": "negative-commercial", "X-Palwakf-Client-Id": "client_a"}, 403, "COMMERCIAL_LEGACY_WRITE_CONTEXT_NOT_SUPPORTED"),
        ("pilot_action_denied", "/api/v1/governed-capability-foundation/pilot/execute", {"workspace_id": "research_learning", "prompt": "A valid longer candidate pilot prompt", "human_reviewer": "operator_a", "explicit_execution_confirmation": True}, {"Authorization": "Bearer research-token"}, 403, "WORKSPACE_ACTION_DENIED"),
    ),
)
def test_authorization_edge_cases_reject_without_mutation(tmp_path: Path, name: str, path: str, payload: dict[str, Any], headers: dict[str, str], status: int, code: str) -> None:
    actors = [
        _actor("operator_a", "gov-token", ["palwakf_government"], ["read", "write", "review"]),
        _actor("operator_a", "research-token", ["research_learning"], ["read", "write"]),
        _actor("operator_a", "read-token", ["palwakf_government"], ["read"]),
        _actor("local.operator", "dotted-token", ["palwakf_government"], ["read"]),
        _actor("operator_a", "commercial-token", ["commercial_projects"], ["read", "write"], ["client_a"]),
    ]
    with _client(tmp_path, actors) as client:
        before = _snapshot(tmp_path)
        response = client.post(path, json=payload, headers=headers)
        after = _snapshot(tmp_path)
    assert response.status_code == status, name
    assert response.json()["detail"]["code"] == code, name
    assert after == before, name
