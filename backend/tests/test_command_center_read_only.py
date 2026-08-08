from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from palwakf_local_agents.command_center.read_only_store import (
    LocalAgentsReadOnlyStore,
    ReadOnlyStoreError,
)
from palwakf_local_agents.command_center.router import mount_command_center


class CommandCenterReadOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in [
            "tasks/inbox",
            "tasks/approved",
            "tasks/archived",
            "audit/human_reviews",
            "output/evidence_manifests",
            "output/evals",
            "reference_sources/approved",
        ]:
            (self.root / rel).mkdir(parents=True, exist_ok=True)

        task = {
            "task_id": "SAPF_DOCUMENTATION_HANDOFF_PILOT_001",
            "title": "Structured payload documentation handoff pilot",
            "status": "APPROVED_FOR_READ_ONLY_RUN",
            "risk": "LOW",
            "autonomy": "L0_READ_ONLY",
            "requested_agent": "documentation_handoff",
            "human_approval_required": True,
        }
        (self.root / "tasks/approved/SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json").write_text(
            json.dumps(task), encoding="utf-8"
        )
        review = {
            "review_id": "HRA-TEST",
            "task_id": task["task_id"],
            "reviewer": "Firas Fanon",
            "decision": "APPROVED_FOR_READ_ONLY_RUN",
            "approval_scope": "MOVE_TO_APPROVED_ONLY_NO_EXECUTION",
            "transition_status": "COMPLETE",
        }
        (self.root / "audit/human_reviews/HRA-TEST.json").write_text(
            json.dumps(review), encoding="utf-8"
        )
        (self.root / "reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md").write_text(
            "# non-sensitive", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_reads_approved_task_without_execution(self) -> None:
        store = LocalAgentsReadOnlyStore(self.root)
        task = store.get_task("SAPF_DOCUMENTATION_HANDOFF_PILOT_001")
        self.assertEqual(task["task"]["status"], "APPROVED_FOR_READ_ONLY_RUN")
        self.assertEqual(task["safety_posture"]["MODEL_EXECUTION"], "NONE")
        self.assertEqual(task["safety_posture"]["PILOT_EXECUTION"], "NOT_EXECUTED")

    def test_rejects_path_traversal_like_task_identifier(self) -> None:
        store = LocalAgentsReadOnlyStore(self.root)
        with self.assertRaises(ReadOnlyStoreError):
            store.get_task("../.env")

    def test_command_center_api_prefix_is_get_only(self) -> None:
        app = FastAPI()
        mount_command_center(app, project_root=self.root)
        client = TestClient(app)

        response = client.get("/api/v1/local-agents/system-health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["active_approved_task_ids"],
            ["SAPF_DOCUMENTATION_HANDOFF_PILOT_001"],
        )
        self.assertEqual(
            client.post("/api/v1/local-agents/dashboard").status_code,
            405,
        )

        command_center_routes = [
            route
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/v1/local-agents")
        ]
        methods = {
            method
            for route in command_center_routes
            for method in getattr(route, "methods", set())
        }
        self.assertFalse({"POST", "PUT", "PATCH", "DELETE"} & methods)

    def test_duplicate_mount_is_rejected(self) -> None:
        app = FastAPI()
        mount_command_center(app, project_root=self.root)
        with self.assertRaises(RuntimeError):
            mount_command_center(app, project_root=self.root)


if __name__ == "__main__":
    unittest.main()
