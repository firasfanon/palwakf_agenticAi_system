from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .policy import load_policy_pack, package_policy_root, validate_identifier


WORKSPACE_SCHEMA_VERSION = "MULTI_WORKSPACE_CORE_POLICY_PACKS_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _decode(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback


BUILTIN_WORKSPACES: tuple[dict[str, str], ...] = (
    {
        "workspace_id": "palwakf_government",
        "display_name": "PalWakf Government",
        "classification": "government",
        "policy_pack_id": "government_strict_v1",
        "lifecycle_state": "active",
        "legacy_data_migration": "NOT_MIGRATED_LEGACY_STATE_REMAINS_SEPARATE",
    },
    {
        "workspace_id": "personal_development",
        "display_name": "Personal Development",
        "classification": "personal",
        "policy_pack_id": "developer_controlled_v1",
        "lifecycle_state": "declared_not_activated",
        "legacy_data_migration": "NOT_APPLICABLE",
    },
    {
        "workspace_id": "commercial_projects",
        "display_name": "Commercial Projects",
        "classification": "commercial",
        "policy_pack_id": "client_isolated_v1",
        "lifecycle_state": "declared_not_activated",
        "legacy_data_migration": "NOT_APPLICABLE",
    },
    {
        "workspace_id": "research_learning",
        "display_name": "Research and Learning",
        "classification": "research",
        "policy_pack_id": "research_read_prepare_v1",
        "lifecycle_state": "declared_not_activated",
        "legacy_data_migration": "NOT_APPLICABLE",
    },
)


@dataclass(frozen=True)
class WorkspaceCoreStore:
    project_root: Path

    @property
    def db_path(self) -> Path:
        return self.project_root / "audit" / "workspace_core.sqlite"

    @property
    def workspace_root(self) -> Path:
        return self.project_root / "workspaces"

    @property
    def policy_root(self) -> Path:
        local = self.project_root / "policy_packs"
        return local if local.is_dir() else package_policy_root()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def initialize(self) -> None:
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS workspace_registry (
                    workspace_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    policy_pack_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    lifecycle_state TEXT NOT NULL,
                    legacy_data_migration TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS workspace_audit_events (
                    sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                    audit_id TEXT NOT NULL UNIQUE,
                    workspace_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT,
                    event_hash TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspace_registry(workspace_id)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS workspace_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_workspace_audit_ws_seq ON workspace_audit_events(workspace_id, sequence_no ASC)")
            con.execute("INSERT OR IGNORE INTO workspace_schema_migrations(version, applied_at) VALUES(?, ?)", (WORKSPACE_SCHEMA_VERSION, _utc_now()))
            for row in BUILTIN_WORKSPACES:
                policy = load_policy_pack(self.policy_root, row["policy_pack_id"])
                now = _utc_now()
                existing = con.execute("SELECT workspace_id FROM workspace_registry WHERE workspace_id=?", (row["workspace_id"],)).fetchone()
                con.execute(
                    """INSERT OR IGNORE INTO workspace_registry(
                    workspace_id,display_name,classification,policy_pack_id,policy_version,lifecycle_state,legacy_data_migration,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (row["workspace_id"], row["display_name"], row["classification"], row["policy_pack_id"], policy["version"], row["lifecycle_state"], row["legacy_data_migration"], now, now),
                )
                if existing is None:
                    self._audit(con, row["workspace_id"], "WORKSPACE_DECLARED", {"policy_pack_id": row["policy_pack_id"], "classification": row["classification"], "lifecycle_state": row["lifecycle_state"]})

    def _audit(self, con: sqlite3.Connection, workspace_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        prior = con.execute("SELECT event_hash FROM workspace_audit_events WHERE workspace_id=? ORDER BY sequence_no DESC LIMIT 1", (workspace_id,)).fetchone()
        previous_hash = prior["event_hash"] if prior else None
        occurred_at = _utc_now()
        audit_id = "WCA-" + _hash(f"{workspace_id}|{event_type}|{occurred_at}|{_json(payload)}")[:16]
        event = {"audit_id": audit_id, "workspace_id": workspace_id, "event_type": event_type, "occurred_at": occurred_at, "payload": payload, "previous_hash": previous_hash}
        event_hash = _hash(_json(event))
        con.execute("""INSERT INTO workspace_audit_events(audit_id,workspace_id,event_type,occurred_at,payload_json,previous_hash,event_hash)
                       VALUES(?,?,?,?,?,?,?)""", (audit_id, workspace_id, event_type, occurred_at, _json(payload), previous_hash, event_hash))
        return {**event, "event_hash": event_hash}

    def _workspace_row(self, workspace_id: str) -> sqlite3.Row:
        workspace_id = validate_identifier(workspace_id, "workspace")
        self.initialize()
        with self._connect() as con:
            row = con.execute("SELECT * FROM workspace_registry WHERE workspace_id=?", (workspace_id,)).fetchone()
        if row is None:
            raise KeyError("WORKSPACE_NOT_FOUND")
        return row

    def _workspace_paths(self, workspace_id: str) -> dict[str, str]:
        workspace_id = validate_identifier(workspace_id, "workspace")
        root = (self.workspace_root / workspace_id).resolve()
        allowed_parent = self.workspace_root.resolve()
        if allowed_parent not in root.parents:
            raise ValueError("CROSS_WORKSPACE_PATH_REJECTED")
        return {
            "workspace_root": f"workspaces/{workspace_id}",
            "state_db": f"workspaces/{workspace_id}/state.sqlite",
            "audit_db": f"workspaces/{workspace_id}/audit.sqlite",
            "evidence_root": f"workspaces/{workspace_id}/evidence",
            "knowledge_root": f"workspaces/{workspace_id}/knowledge",
            "memory_root": f"workspaces/{workspace_id}/memory",
        }

    def _public_workspace(self, row: sqlite3.Row) -> dict[str, Any]:
        policy = load_policy_pack(self.policy_root, row["policy_pack_id"])
        return {
            "workspace_id": row["workspace_id"],
            "display_name": row["display_name"],
            "classification": row["classification"],
            "policy_pack_id": row["policy_pack_id"],
            "policy_version": row["policy_version"],
            "lifecycle_state": row["lifecycle_state"],
            "legacy_data_migration": row["legacy_data_migration"],
            "execution_mode": policy["execution"]["execution_mode"],
            "workspace_paths": self._workspace_paths(row["workspace_id"]),
            "isolation_contract": "NO_CROSS_WORKSPACE_READ_WRITE_TOOL_MEMORY_OR_AUDIT_ACCESS",
        }

    def list_workspaces(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._connect() as con:
            rows = con.execute("SELECT * FROM workspace_registry ORDER BY workspace_id ASC").fetchall()
        return [self._public_workspace(row) for row in rows]

    def workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._public_workspace(self._workspace_row(workspace_id))

    def policy(self, workspace_id: str) -> dict[str, Any]:
        row = self._workspace_row(workspace_id)
        policy = load_policy_pack(self.policy_root, row["policy_pack_id"])
        return {
            "workspace_id": row["workspace_id"],
            "policy_pack_id": policy["policy_pack_id"],
            "version": policy["version"],
            "classification": policy["classification"],
            "execution": policy["execution"],
            "review": policy["review"],
            "tools": policy["tools"],
            "memory": policy["memory"],
            "audit": policy["audit"],
            "integration": policy["integration"],
            "non_transferable_constraints": policy["non_transferable_constraints"],
        }

    def readiness(self, workspace_id: str) -> dict[str, Any]:
        row = self._workspace_row(workspace_id)
        policy = load_policy_pack(self.policy_root, row["policy_pack_id"])
        return {
            "workspace_id": row["workspace_id"],
            "lifecycle_state": row["lifecycle_state"],
            "policy_bound": True,
            "policy_pack_versioned": bool(policy.get("version")),
            "workspace_storage_initialized": False,
            "legacy_state_migrated": row["legacy_data_migration"] == "MIGRATED",
            "execution_gateway": policy["execution"]["execution_gateway"],
            "model_execution": policy["execution"]["model_execution"],
            "pilot_execution": policy["execution"]["pilot_execution"],
            "human_review": policy["review"]["human_review"],
            "next_authorized_step": "WORKSPACE_STORAGE_AND_OPERATIONS_BINDING_REQUIRES_SEPARATE_APPROVAL",
        }

    def audit_integrity(self, workspace_id: str) -> dict[str, Any]:
        row = self._workspace_row(workspace_id)
        workspace_id = row["workspace_id"]
        with self._connect() as con:
            events = con.execute("SELECT * FROM workspace_audit_events WHERE workspace_id=? ORDER BY sequence_no ASC", (workspace_id,)).fetchall()
        previous_hash = None
        failures: list[str] = []
        for event in events:
            payload = _decode(event["payload_json"], {})
            expected = _hash(_json({"audit_id": event["audit_id"], "workspace_id": workspace_id, "event_type": event["event_type"], "occurred_at": event["occurred_at"], "payload": payload, "previous_hash": previous_hash}))
            if event["previous_hash"] != previous_hash or event["event_hash"] != expected:
                failures.append(event["audit_id"])
            previous_hash = event["event_hash"]
        return {"workspace_id": workspace_id, "audit_chain_integrity": "PASS" if not failures else "FAIL", "event_count": len(events), "failures": failures}

    def health(self) -> dict[str, Any]:
        workspaces = self.list_workspaces()
        return {
            "health": "MULTI_WORKSPACE_CORE_READY",
            "registry_state": "LOCAL_SQLITE_ONLY_ON_FIRST_RUNTIME_ACCESS",
            "registry_path_scope": "audit/workspace_core.sqlite",
            "workspace_root_scope": "workspaces/<workspace_id>/",
            "workspace_count": len(workspaces),
            "policy_pack_count": len({item["policy_pack_id"] for item in workspaces}),
            "cross_workspace_access": "REJECTED_BY_CONTRACT",
            "legacy_governed_operations": "UNCHANGED_NOT_MIGRATED",
            "model_execution_default": "NONE",
            "pilot_execution_default": "NOT_EXECUTED",
            "platform_mutation": "NONE",
            "external_database_access": "NONE",
            "git_write": "NONE",
            "deployment": "NONE",
            "secrets_access": "NONE",
            "memory_write": "NONE",
        }
