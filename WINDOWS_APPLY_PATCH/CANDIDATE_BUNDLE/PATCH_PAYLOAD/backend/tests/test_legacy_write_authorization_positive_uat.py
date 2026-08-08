from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from palwakf_local_agents import store as legacy_store
from palwakf_local_agents.app import create_app


def _snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    return result


def _changed_paths(before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {path for path in (set(before) | set(after)) if before.get(path) != after.get(path)}


def _idempotent(headers: dict[str, str], key: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": key}


def test_controlled_positive_authorization_uat_is_government_only_and_non_executing(
    authorized_project: Path,
    governed_headers: dict[str, str],
    local_agent_headers: dict[str, str],
    foundation_headers: dict[str, str],
) -> None:
    """Prove controlled local writes in explicitly bounded disposable scopes.

    The test deliberately excludes commercial tenancy, React write controls, pilot
    execution, external network, database/platform bridges, and any real actor
    provisioning. Government routes cover legacy operations and local preparations;
    the capability-foundation write is restricted to research_learning because the
    foundation does not enable persistent writes for palwakf_government.
    """
    legacy_store.PROJECT_ROOT = authorized_project
    legacy_store.DB_PATH = authorized_project / "audit" / "local_agents.sqlite"

    app = create_app(authorized_project)
    # Capability Foundation has no public bootstrap route. Seed only the disposable
    # research fixture before the UAT baseline; this is not a user-facing write and
    # is intentionally excluded from the measured postimage.
    app.state.governed_capability_foundation_store.initialize_workspace("research_learning")

    with TestClient(app) as client:
        before = _snapshot(authorized_project)

        foundation_task = client.post(
            "/api/v1/governed-capability-foundation/workspaces/research_learning/tasks",
            json={"title": "Positive authorization foundation task", "description": "Disposable local-only authorization UAT record."},
            headers=foundation_headers,
        )
        assert foundation_task.status_code == 201
        assert foundation_task.json()["workspace_id"] == "research_learning"
        assert foundation_task.json()["created_by"] == "foundation.operator"

        governed_task = client.post(
            "/api/v1/governed-operations/workspaces/palwakf_government/tasks",
            json={
                "title": "Positive authorization governed task",
                "request": "Exercise the controlled local authorization path without model or pilot execution.",
                "system_scope": "local_agents",
                "risk_level": "medium",
                "requested_by": "test_operator",
                "requested_roles": [],
                "allowed_paths": [],
                "forbidden_actions": ["model_execution", "platform_mutation", "database_access"],
                "evidence_required": ["source_verification"],
            },
            headers=_idempotent(governed_headers, "positive-auth-governed-task-0001"),
        )
        assert governed_task.status_code == 201
        task = governed_task.json()["task"]
        assert task["execution_state"] == "NOT_EXECUTED"
        assert task["permission_intersection"]["model_execution"] == "NONE"

        submitted = client.post(
            f"/api/v1/governed-operations/workspaces/palwakf_government/tasks/{task['task_id']}/submit",
            json={"actor_id": "test_operator", "rationale": "Submit controlled local UAT record for human review.", "evidence_ids": [], "expected_version": task["version"]},
            headers=governed_headers,
        )
        assert submitted.status_code == 200
        task = submitted.json()["task"]

        reviewing = client.post(
            f"/api/v1/governed-operations/workspaces/palwakf_government/tasks/{task['task_id']}/start-review",
            json={"actor_id": "test_operator", "rationale": "Start controlled local human review for the UAT record.", "evidence_ids": [], "expected_version": task["version"]},
            headers=governed_headers,
        )
        assert reviewing.status_code == 200
        task = reviewing.json()["task"]

        evidence = client.post(
            "/api/v1/governed-operations/workspaces/palwakf_government/evidence",
            json={
                "actor_id": "test_operator",
                "task_id": task["task_id"],
                "category": "source_verification",
                "source_type": "local_test",
                "trust_level": "verified",
                "raw_status": "verified",
                "summary": "Controlled positive authorization UAT evidence.",
                "source_reference": "local://positive-authorization-uat",
                "metadata": {"scope": "government_only", "execution": "none"},
            },
            headers=governed_headers,
        )
        assert evidence.status_code == 201

        approved = client.post(
            f"/api/v1/governed-operations/workspaces/palwakf_government/tasks/{task['task_id']}/review",
            json={
                "actor_id": "test_operator",
                "rationale": "Approve only the local test record after the required evidence exists.",
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

        preparation = client.post(
            "/api/v1/local-agent-core/workspaces/palwakf_government/preparations",
            json={
                "agent_id": "task_planning_runbook_agent_v1",
                "objective": "Prepare a controlled authorization UAT handoff without model or pilot execution.",
                "requested_by": "local.operator",
                "requested_capabilities": ["mega_batch_plan"],
                "source_summary": "MODEL_EXECUTION=NONE; PILOT_EXECUTION=NOT_EXECUTED",
                "evidence_references": ["POS-AUTH-UAT-001"],
            },
            headers=_idempotent(local_agent_headers, "positive-auth-local-preparation-0001"),
        )
        assert preparation.status_code == 201
        preparation_item = preparation.json()["preparation"]
        assert preparation_item["execution_state"] == "NOT_EXECUTED"
        assert preparation_item["model_execution"] == "NONE"
        assert preparation_item["pilot_execution"] == "NOT_EXECUTED"

        after = _snapshot(authorized_project)

    changed = _changed_paths(before, after)
    allowed_exact = {
        "workspaces/research_learning/capability_foundation.sqlite",
        "workspaces/palwakf_government/governed_operations.sqlite",
        "workspaces/palwakf_government/local_agent_core.sqlite",
        "evidence/ledger/ledger_contract.json",
        "evidence/ledger/entries.jsonl",
    }
    assert changed <= allowed_exact
    assert not any(path.startswith("workspaces/personal_development/") for path in changed)
    assert not any(path.startswith("workspaces/commercial_projects/") for path in changed)
    assert not any(
        path.startswith("workspaces/research_learning/")
        and path != "workspaces/research_learning/capability_foundation.sqlite"
        for path in changed
    )
