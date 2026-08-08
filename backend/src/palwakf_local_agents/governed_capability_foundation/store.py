from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from palwakf_local_agents.workspace_core.policy import validate_identifier
from palwakf_local_agents.workspace_core.store import WorkspaceCoreStore

from .authz import ActorPrincipal, require_commercial_client_scope
from .tools import deterministic_tool

SCHEMA_VERSION = "GOVERNED_CAPABILITY_FOUNDATION_V1_AUTHORIZATION_BOUNDARY_V1"
FOUNDATION_WORKSPACES = {"personal_development", "commercial_projects", "research_learning"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _error(status_code: int, code: str, **extra: Any) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, **extra})


@dataclass(frozen=True)
class GovernedCapabilityFoundationStore:
    project_root: Path

    @property
    def workspace_core(self) -> WorkspaceCoreStore:
        return WorkspaceCoreStore(self.project_root)

    @property
    def evidence_root(self) -> Path:
        return self.project_root / "evidence" / "ledger"

    @property
    def pilot_config_path(self) -> Path:
        return self.project_root / "config" / "controlled_first_prompt_pilot_v1.json"

    def _workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = validate_identifier(workspace_id, "workspace")
        try:
            return self.workspace_core.workspace(workspace_id)
        except KeyError:
            _error(404, "WORKSPACE_NOT_FOUND", workspace_id=workspace_id)
        raise AssertionError("unreachable")

    def _commercial_client_id(self, workspace_id: str, client_id: str | None, actor: ActorPrincipal) -> str | None:
        if workspace_id != "commercial_projects":
            if client_id is not None:
                _error(400, "CLIENT_CONTEXT_NOT_ALLOWED_OUTSIDE_COMMERCIAL_WORKSPACE")
            return None
        if not client_id:
            _error(400, "COMMERCIAL_CLIENT_CONTEXT_REQUIRED")
        return require_commercial_client_scope(actor, client_id)

    def db_path(self, workspace_id: str) -> Path:
        workspace_id = validate_identifier(workspace_id, "workspace")
        if workspace_id not in FOUNDATION_WORKSPACES:
            _error(403, "WORKSPACE_FOUNDATION_NOT_ENABLED", workspace_id=workspace_id)
        root = (self.project_root / "workspaces" / workspace_id).resolve()
        parent = (self.project_root / "workspaces").resolve()
        if parent not in root.parents:
            _error(400, "CROSS_WORKSPACE_PATH_REJECTED")
        return root / "capability_foundation.sqlite"

    def _connect(self, workspace_id: str, initialize: bool = False) -> sqlite3.Connection:
        path = self.db_path(workspace_id)
        if initialize:
            path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() and not initialize:
            _error(404, "WORKSPACE_FOUNDATION_NOT_INITIALIZED", workspace_id=workspace_id)
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _audit(self, con: sqlite3.Connection, workspace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        prior = con.execute("SELECT event_hash FROM audit_events ORDER BY sequence_no DESC LIMIT 1").fetchone()
        previous_hash = prior["event_hash"] if prior else None
        occurred_at = _utc_now()
        audit_id = "GCF-" + _hash(f"{workspace_id}|{event_type}|{occurred_at}|{_json(payload)}")[:18]
        record = {"audit_id": audit_id, "workspace_id": workspace_id, "event_type": event_type, "occurred_at": occurred_at, "payload": payload, "previous_hash": previous_hash}
        con.execute(
            "INSERT INTO audit_events(audit_id,workspace_id,event_type,occurred_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)",
            (audit_id, workspace_id, event_type, occurred_at, _json(payload), previous_hash, _hash(_json(record))),
        )

    def _ensure_column(self, con: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        names = {str(row["name"]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in names:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def initialize_workspace(self, workspace_id: str) -> bool:
        workspace = self._workspace(workspace_id)
        if workspace_id not in FOUNDATION_WORKSPACES:
            return False
        bound_now = False
        with self._connect(workspace_id, initialize=True) as con:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, state TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, client_id TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS projects(project_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL, state TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, client_id TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS review_records(review_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, subject_type TEXT NOT NULL, subject_id TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL, rationale TEXT NOT NULL, created_at TEXT NOT NULL, client_id TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS tool_runs(run_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, tool_name TEXT NOT NULL, input_hash TEXT NOT NULL, output_json TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, client_id TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS audit_events(sequence_no INTEGER PRIMARY KEY AUTOINCREMENT, audit_id TEXT NOT NULL UNIQUE, workspace_id TEXT NOT NULL, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, payload_json TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL)")
            for table in ("tasks", "projects", "review_records", "tool_runs"):
                self._ensure_column(con, table, "client_id", "client_id TEXT")
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_ws_created ON tasks(workspace_id, created_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_projects_ws_created ON projects(workspace_id, created_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(workspace_id, client_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(workspace_id, client_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_audit_seq ON audit_events(sequence_no ASC)")
            con.execute("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(?, ?)", (SCHEMA_VERSION, _utc_now()))
            existing = con.execute("SELECT 1 FROM audit_events WHERE event_type='WORKSPACE_CAPABILITY_AUTHORIZATION_BOUND' LIMIT 1").fetchone()
            if existing is None:
                bound_now = True
                self._audit(con, workspace_id, "WORKSPACE_CAPABILITY_AUTHORIZATION_BOUND", {"policy_pack_id": workspace["policy_pack_id"], "scope": "ACTOR_SCOPED_AND_CLIENT_ISOLATED"})
        return bound_now

    def initialize_all(self) -> None:
        self._write_ledger_contract()
        for workspace_id in sorted(FOUNDATION_WORKSPACES):
            if self.initialize_workspace(workspace_id):
                self._append_evidence({"event_type": "WORKSPACE_CAPABILITY_AUTHORIZATION_BOUND", "workspace_id": workspace_id, "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED"})

    def _write_ledger_contract(self) -> None:
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        contract = self.evidence_root / "ledger_contract.json"
        desired = {"contract": "DURABLE_EVIDENCE_LEDGER_V1", "storage": "PROJECT_PERSISTENT", "cross_workspace_read": "DENY_BY_DEFAULT", "actor_authentication": "REQUIRED", "client_isolation": "REQUIRED_FOR_COMMERCIAL", "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED"}
        if not contract.exists():
            contract.write_text(_json(desired) + "\n", encoding="utf-8")
        entries = self.evidence_root / "entries.jsonl"
        entries.touch(exist_ok=True)

    def _append_evidence(self, event: dict[str, Any]) -> None:
        self._write_ledger_contract()
        entries = self.evidence_root / "entries.jsonl"
        prior = None
        if entries.stat().st_size:
            for line in reversed(entries.read_text(encoding="utf-8").splitlines()):
                if line.strip():
                    prior = json.loads(line).get("event_hash")
                    break
        record = {"occurred_at": _utc_now(), "previous_hash": prior, **event}
        record["event_hash"] = _hash(_json(record))
        with entries.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_json(record) + "\n")

    def health(self) -> dict[str, Any]:
        return {"contract": SCHEMA_VERSION, "authorization_boundary": "ACTOR_SCOPE_AND_CLIENT_SCOPE_REQUIRED", "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED", "shell_execution": "NONE", "git_write": "NONE", "external_network": "NONE", "foundation_workspaces": sorted(FOUNDATION_WORKSPACES)}

    def workspace_status(self, workspace_id: str, actor: ActorPrincipal) -> dict[str, Any]:
        self._workspace(workspace_id)
        if workspace_id == "palwakf_government":
            manifest = self.project_root / "workspaces" / workspace_id / "workspace_manifest.json"
            return {"workspace_id": workspace_id, "foundation_state": "POLICY_MANIFEST_AND_REVIEW_CONTEXT_ONLY", "manifest_present": manifest.is_file(), "actor_id": actor.actor_id, "local_agent_core_sqlite_mutation": "NONE", "model_execution": "NONE"}
        path = self.db_path(workspace_id)
        return {"workspace_id": workspace_id, "foundation_state": "INITIALIZED" if path.is_file() else "NOT_INITIALIZED", "database": str(path.relative_to(self.project_root)).replace("\\", "/"), "actor_id": actor.actor_id, "cross_workspace_access": "DENY_BY_ACTOR_SCOPE", "model_execution": "NONE"}

    def _rows(self, workspace_id: str, table: str, actor: ActorPrincipal) -> list[dict[str, Any]]:
        self._workspace(workspace_id)
        with self._connect(workspace_id) as con:
            if workspace_id == "commercial_projects":
                if not actor.commercial_client_scopes:
                    _error(403, "COMMERCIAL_CLIENT_SCOPE_DENIED", actor_id=actor.actor_id)
                marks = ",".join("?" for _ in actor.commercial_client_scopes)
                rows = con.execute(f"SELECT * FROM {table} WHERE client_id IN ({marks}) ORDER BY created_at DESC", tuple(sorted(actor.commercial_client_scopes))).fetchall()
            else:
                rows = con.execute(f"SELECT * FROM {table} ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def list_tasks(self, workspace_id: str, actor: ActorPrincipal) -> list[dict[str, Any]]:
        return self._rows(workspace_id, "tasks", actor)

    def list_projects(self, workspace_id: str, actor: ActorPrincipal) -> list[dict[str, Any]]:
        return self._rows(workspace_id, "projects", actor)

    def create_task(self, workspace_id: str, title: str, description: str, client_id: str | None, actor: ActorPrincipal) -> dict[str, Any]:
        self._workspace(workspace_id)
        client_id = self._commercial_client_id(workspace_id, client_id, actor)
        item = {"task_id": "TSK-" + uuid.uuid4().hex[:18].upper(), "workspace_id": workspace_id, "title": title, "description": description, "state": "open", "created_by": actor.actor_id, "created_at": _utc_now(), "client_id": client_id}
        with self._connect(workspace_id) as con:
            con.execute("INSERT INTO tasks(task_id,workspace_id,title,description,state,created_by,created_at,client_id) VALUES(?,?,?,?,?,?,?,?)", tuple(item.values()))
            self._audit(con, workspace_id, "TASK_CREATED", {"task_id": item["task_id"], "actor_id": actor.actor_id, "client_id": client_id})
        self._append_evidence({"event_type": "TASK_CREATED", "workspace_id": workspace_id, "subject_id": item["task_id"], "actor_id": actor.actor_id, "client_id": client_id, "model_execution": "NONE"})
        return item

    def create_project(self, workspace_id: str, name: str, description: str, client_id: str | None, actor: ActorPrincipal) -> dict[str, Any]:
        self._workspace(workspace_id)
        client_id = self._commercial_client_id(workspace_id, client_id, actor)
        item = {"project_id": "PRJ-" + uuid.uuid4().hex[:18].upper(), "workspace_id": workspace_id, "name": name, "description": description, "state": "open", "created_by": actor.actor_id, "created_at": _utc_now(), "client_id": client_id}
        with self._connect(workspace_id) as con:
            con.execute("INSERT INTO projects(project_id,workspace_id,name,description,state,created_by,created_at,client_id) VALUES(?,?,?,?,?,?,?,?)", tuple(item.values()))
            self._audit(con, workspace_id, "PROJECT_CREATED", {"project_id": item["project_id"], "actor_id": actor.actor_id, "client_id": client_id})
        self._append_evidence({"event_type": "PROJECT_CREATED", "workspace_id": workspace_id, "subject_id": item["project_id"], "actor_id": actor.actor_id, "client_id": client_id, "model_execution": "NONE"})
        return item

    def review(self, workspace_id: str, subject_type: str, subject_id: str, decision: str, rationale: str, client_id: str | None, actor: ActorPrincipal) -> dict[str, Any]:
        self._workspace(workspace_id)
        client_id = self._commercial_client_id(workspace_id, client_id, actor)
        item = {"review_id": "REV-" + uuid.uuid4().hex[:18].upper(), "workspace_id": workspace_id, "subject_type": subject_type, "subject_id": subject_id, "reviewer": actor.actor_id, "decision": decision, "rationale": rationale, "created_at": _utc_now(), "client_id": client_id}
        with self._connect(workspace_id) as con:
            con.execute("INSERT INTO review_records(review_id,workspace_id,subject_type,subject_id,reviewer,decision,rationale,created_at,client_id) VALUES(?,?,?,?,?,?,?,?,?)", tuple(item.values()))
            self._audit(con, workspace_id, "HUMAN_REVIEW_RECORDED", {"review_id": item["review_id"], "actor_id": actor.actor_id, "client_id": client_id})
        self._append_evidence({"event_type": "HUMAN_REVIEW_RECORDED", "workspace_id": workspace_id, "subject_id": item["review_id"], "actor_id": actor.actor_id, "client_id": client_id, "model_execution": "NONE"})
        return item

    def tool(self, workspace_id: str, tool_name: str, text: str, client_id: str | None, actor: ActorPrincipal) -> dict[str, Any]:
        self._workspace(workspace_id)
        client_id = self._commercial_client_id(workspace_id, client_id, actor)
        try:
            output = deterministic_tool(tool_name, text)
        except KeyError:
            _error(403, "DETERMINISTIC_TOOL_NOT_ALLOWED", tool_name=tool_name)
        run_id = "TLR-" + uuid.uuid4().hex[:18].upper()
        created_at = _utc_now()
        with self._connect(workspace_id) as con:
            con.execute("INSERT INTO tool_runs(run_id,workspace_id,tool_name,input_hash,output_json,created_by,created_at,client_id) VALUES(?,?,?,?,?,?,?,?)", (run_id, workspace_id, tool_name, _hash(text), _json(output), actor.actor_id, created_at, client_id))
            self._audit(con, workspace_id, "DETERMINISTIC_TOOL_PREPARED", {"run_id": run_id, "actor_id": actor.actor_id, "client_id": client_id, "tool_name": tool_name})
        self._append_evidence({"event_type": "DETERMINISTIC_TOOL_PREPARED", "workspace_id": workspace_id, "subject_id": run_id, "actor_id": actor.actor_id, "client_id": client_id, "tool_name": tool_name, "model_execution": "NONE"})
        return {"run_id": run_id, "workspace_id": workspace_id, "tool_name": tool_name, "output": output, "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED"}

    def pilot_status(self, actor: ActorPrincipal) -> dict[str, Any]:
        if not self.pilot_config_path.is_file():
            _error(404, "PILOT_CONFIGURATION_NOT_FOUND")
        config = json.loads(self.pilot_config_path.read_text(encoding="utf-8"))
        return {"workspace_id": config["pilot_workspace_id"], "human_reviewer": config["human_reviewer"], "actor_id": actor.actor_id, "model": config["provider"]["model"], "endpoint": config["provider"]["endpoint"], "pilot_execution": "NOT_EXECUTED", "requires_explicit_runtime_confirmation": True, "allowed_tools": "NONE"}

    def execute_pilot(self, workspace_id: str, prompt: str, human_reviewer: str, explicit_execution_confirmation: bool, actor: ActorPrincipal) -> dict[str, Any]:
        if not explicit_execution_confirmation:
            _error(403, "PILOT_EXPLICIT_RUNTIME_CONFIRMATION_REQUIRED")
        if not self.pilot_config_path.is_file():
            _error(404, "PILOT_CONFIGURATION_NOT_FOUND")
        config = json.loads(self.pilot_config_path.read_text(encoding="utf-8"))
        if actor.actor_id != config["human_reviewer"].lower() or human_reviewer != config["human_reviewer"]:
            _error(403, "PILOT_HUMAN_REVIEWER_IDENTITY_MISMATCH")
        if workspace_id != config["pilot_workspace_id"] or prompt != config["pilot_prompt"]:
            _error(403, "PILOT_PAYLOAD_MISMATCH")
        _error(403, "PILOT_EXECUTION_REQUIRES_SEPARATE_EXPLICIT_AUTHORIZATION")
