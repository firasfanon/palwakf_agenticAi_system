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

from .contracts import AgentPreparationCreate, ModelPilotDraftCreate
from .engine import prepare
from .policy import assess_model_pilot, assess_request, controls_for_workspace
from .registry import get_agent, list_agents
from .model_pilot import generate_local_draft, load_model_pilot_config, pilot_status

SCHEMA_VERSION = "GOVERNED_LOCAL_AGENT_CORE_V1"
MODEL_PILOT_SCHEMA_VERSION = "LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _error(status_code: int, code: str, **extra: Any) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, **extra})


@dataclass(frozen=True)
class LocalAgentCoreStore:
    project_root: Path

    @property
    def workspace_core(self) -> WorkspaceCoreStore:
        return WorkspaceCoreStore(self.project_root)

    def db_path(self, workspace_id: str) -> Path:
        workspace_id = validate_identifier(workspace_id, "workspace")
        root = (self.project_root / "workspaces" / workspace_id).resolve()
        parent = (self.project_root / "workspaces").resolve()
        if parent not in root.parents:
            raise ValueError("CROSS_WORKSPACE_PATH_REJECTED")
        return root / "local_agent_core.sqlite"

    def _workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = validate_identifier(workspace_id, "workspace")
        try:
            return self.workspace_core.workspace(workspace_id)
        except KeyError:
            _error(404, "WORKSPACE_NOT_FOUND", workspace_id=workspace_id)
        raise AssertionError("unreachable")

    def _connect(self, workspace_id: str, initialize: bool = False) -> sqlite3.Connection | None:
        path = self.db_path(workspace_id)
        if not initialize and not path.exists():
            return None
        if initialize:
            path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def initialize_workspace(self, workspace_id: str) -> None:
        workspace = self._workspace(workspace_id)
        controls = controls_for_workspace(self.workspace_core, workspace_id, "policy_guardian_agent_v1")
        with self._connect(workspace_id, initialize=True) as con:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            con.execute("""CREATE TABLE IF NOT EXISTS agent_preparations (
                preparation_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, payload_fingerprint TEXT NOT NULL,
                workspace_id TEXT NOT NULL, agent_id TEXT NOT NULL, policy_snapshot_json TEXT NOT NULL,
                request_json TEXT NOT NULL, output_json TEXT NOT NULL, preparation_state TEXT NOT NULL,
                execution_state TEXT NOT NULL, model_execution TEXT NOT NULL, pilot_execution TEXT NOT NULL,
                requested_by TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT NOT NULL,
                input_hash TEXT NOT NULL, output_hash TEXT NOT NULL
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS review_packets (
                review_packet_id TEXT PRIMARY KEY, preparation_id TEXT NOT NULL UNIQUE, workspace_id TEXT NOT NULL,
                packet_json TEXT NOT NULL, created_at TEXT NOT NULL, packet_hash TEXT NOT NULL,
                FOREIGN KEY(preparation_id) REFERENCES agent_preparations(preparation_id)
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT, audit_id TEXT NOT NULL UNIQUE,
                preparation_id TEXT, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL,
                FOREIGN KEY(preparation_id) REFERENCES agent_preparations(preparation_id)
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_agent_preparations_created ON agent_preparations(created_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_agent_audit_sequence ON audit_events(sequence_no ASC)")
            con.execute("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)", (SCHEMA_VERSION, _utc_now()))
            con.execute("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)", (MODEL_PILOT_SCHEMA_VERSION, _utc_now()))
            existing = con.execute("SELECT 1 FROM audit_events WHERE event_type='LOCAL_AGENT_CORE_BOUND' LIMIT 1").fetchone()
            if existing is None:
                self._audit(con, None, "LOCAL_AGENT_CORE_BOUND", {"workspace_id": workspace["workspace_id"], "policy_pack_id": controls["policy_pack_id"], "scope": "LOCAL_DETERMINISTIC_PREPARE_ONLY"})

    def _audit(self, con: sqlite3.Connection, preparation_id: str | None, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        prior = con.execute("SELECT event_hash FROM audit_events ORDER BY sequence_no DESC LIMIT 1").fetchone()
        previous_hash = prior["event_hash"] if prior else None
        occurred_at = _utc_now()
        audit_id = "LAA-" + _hash(f"{preparation_id}|{event_type}|{occurred_at}|{_json(payload)}")[:18]
        record = {"audit_id": audit_id, "preparation_id": preparation_id, "event_type": event_type, "occurred_at": occurred_at, "payload": payload, "previous_hash": previous_hash}
        event_hash = _hash(_json(record))
        con.execute("INSERT INTO audit_events(audit_id,preparation_id,event_type,occurred_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)", (audit_id, preparation_id, event_type, occurred_at, _json(payload), previous_hash, event_hash))
        return {**record, "event_hash": event_hash}

    def health(self) -> dict[str, Any]:
        workspaces = self.workspace_core.list_workspaces()
        status = pilot_status(self.project_root)
        return {
            "health": "GOVERNED_LOCAL_AGENT_CORE_READY",
            "agent_count": len(list_agents()),
            "workspace_count": len(workspaces),
            "agent_runtime": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
            "core_agent_operating_model": "CORE_AGENT_OPERATING_MODEL_V1",
            "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
            "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
            "local_model_adapter": "OLLAMA_LOCAL_ONLY_DISABLED_BY_DEFAULT",
            "model_execution": "NONE",
            "pilot_execution": "NOT_EXECUTED",
            "controlled_model_pilot": status,
            "workspace_scoping": "REQUIRED",
            "cross_workspace_access": "DENY",
            "storage": "PER_WORKSPACE_LOCAL_SQLITE_ON_EXPLICIT_HUMAN_PREPARE_ONLY_ACTION",
            "memory_write": "NONE",
            "shell_execution": "NONE",
            "git_write": "NONE",
            "database_write": "NONE",
            "deployment": "NONE",
            "external_network": "NONE",
        }

    def list_agents(self) -> list[dict[str, Any]]:
        return list_agents()

    def workspace_agents(self, workspace_id: str) -> list[dict[str, Any]]:
        self._workspace(workspace_id)
        return [{**agent, "controls": controls_for_workspace(self.workspace_core, workspace_id, agent["agent_id"])} for agent in list_agents()]

    def controls(self, workspace_id: str, agent_id: str) -> dict[str, Any]:
        self._workspace(workspace_id)
        try:
            return controls_for_workspace(self.workspace_core, workspace_id, agent_id)
        except KeyError:
            _error(404, "LOCAL_AGENT_NOT_FOUND", agent_id=agent_id)
        raise AssertionError("unreachable")

    def memory_boundary(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        return {"workspace_id": workspace["workspace_id"], "memory_scope": f"workspaces/{workspace['workspace_id']}/memory", "memory_write": "NONE", "shared_memory": "FORBIDDEN", "cross_workspace_memory": "FORBIDDEN", "legacy_memory_migration": "NONE"}

    def _preparation_view(self, row: sqlite3.Row) -> dict[str, Any]:
        return {"preparation_id": row["preparation_id"], "workspace_id": row["workspace_id"], "agent_id": row["agent_id"], "policy_snapshot": _decode(row["policy_snapshot_json"], {}), "request": _decode(row["request_json"], {}), "output": _decode(row["output_json"], {}), "preparation_state": row["preparation_state"], "execution_state": row["execution_state"], "model_execution": row["model_execution"], "pilot_execution": row["pilot_execution"], "requested_by": row["requested_by"], "created_at": row["created_at"], "completed_at": row["completed_at"], "input_hash": row["input_hash"], "output_hash": row["output_hash"]}

    def create_preparation(self, workspace_id: str, payload: AgentPreparationCreate, idempotency_key: str) -> tuple[dict[str, Any], bool]:
        self._workspace(workspace_id)
        if not idempotency_key or len(idempotency_key) > 160:
            _error(400, "IDEMPOTENCY_KEY_REQUIRED")
        try:
            get_agent(payload.agent_id)
        except KeyError:
            _error(404, "LOCAL_AGENT_NOT_FOUND", agent_id=payload.agent_id)
        controls = self.controls(workspace_id, payload.agent_id)
        assessment = assess_request(controls, payload.requested_capabilities)
        if assessment["decision"] != "PREPARE_ALLOWED":
            _error(403, "LOCAL_AGENT_PREPARATION_DENIED", decision=assessment)
        self.initialize_workspace(workspace_id)
        fingerprint = _hash(_json(payload.model_dump(mode="json")))
        with self._connect(workspace_id, initialize=True) as con:
            existing = con.execute("SELECT * FROM agent_preparations WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing is not None:
                if existing["payload_fingerprint"] != fingerprint:
                    _error(409, "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")
                return self._preparation_view(existing), True
            output = prepare(payload.agent_id, payload.objective, payload.source_summary, payload.evidence_references, assessment, payload.task_id)
            preparation_id = "LAP-" + uuid.uuid4().hex[:20].upper(); now = _utc_now()
            input_hash = _hash(_json(payload.model_dump(mode="json"))); output_hash = _hash(_json(output))
            con.execute("""INSERT INTO agent_preparations(preparation_id,idempotency_key,payload_fingerprint,workspace_id,agent_id,policy_snapshot_json,request_json,output_json,preparation_state,execution_state,model_execution,pilot_execution,requested_by,created_at,completed_at,input_hash,output_hash)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (preparation_id, idempotency_key, fingerprint, workspace_id, payload.agent_id, _json(controls), _json(payload.model_dump(mode="json")), _json(output), "PREPARED_FOR_HUMAN_REVIEW", "NOT_EXECUTED", "NONE", "NOT_EXECUTED", payload.requested_by, now, now, input_hash, output_hash))
            packet = {"workspace_id": workspace_id, "task_id": payload.task_id, "preparation_id": preparation_id, "agent_id": payload.agent_id, "core_agent_operating_model": "CORE_AGENT_OPERATING_MODEL_V1", "workspace_task_binding": "TASK_ID_BOUND" if payload.task_id else "TASK_ID_NOT_SUPPLIED_PREPARE_ONLY", "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION", "execution_state": "NOT_EXECUTED", "model_execution": "NONE", "policy_decision": assessment, "evidence_references": payload.evidence_references, "review_prompts": ["Confirm workspace boundary.", "Confirm governed task binding when operational activation is requested.", "Confirm preparation-only output.", "Confirm no execution authority is granted."], "approval_effect": "NO_EXECUTION_AUTHORITY_GRANTED"}
            packet_id = "LRP-" + uuid.uuid4().hex[:20].upper(); packet_hash = _hash(_json(packet))
            con.execute("INSERT INTO review_packets(review_packet_id,preparation_id,workspace_id,packet_json,created_at,packet_hash) VALUES(?,?,?,?,?,?)", (packet_id, preparation_id, workspace_id, _json(packet), now, packet_hash))
            self._audit(con, preparation_id, "LOCAL_AGENT_PREPARED", {"agent_id": payload.agent_id, "task_id": payload.task_id, "core_agent_operating_model": "CORE_AGENT_OPERATING_MODEL_V1", "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION", "execution_state": "NOT_EXECUTED", "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED", "output_hash": output_hash, "review_packet_id": packet_id})
            row = con.execute("SELECT * FROM agent_preparations WHERE preparation_id=?", (preparation_id,)).fetchone()
        return self._preparation_view(row), False

    def model_pilot_status(self, workspace_id: str) -> dict[str, Any]:
        self._workspace(workspace_id)
        status = pilot_status(self.project_root)
        controls = self.controls(workspace_id, status["agent_id"])
        decision = assess_model_pilot(controls, workspace_id, status["agent_id"], status["pilot_enabled"])
        return {**status, "workspace_id": workspace_id, "decision": decision["decision"], "decision_reason": decision["reason"]}

    def create_model_pilot_draft(self, workspace_id: str, payload: ModelPilotDraftCreate, idempotency_key: str) -> tuple[dict[str, Any], bool]:
        self._workspace(workspace_id)
        if not idempotency_key or len(idempotency_key) > 160:
            _error(400, "IDEMPOTENCY_KEY_REQUIRED")
        config = load_model_pilot_config(self.project_root)
        controls = self.controls(workspace_id, payload.agent_id)
        assessment = assess_model_pilot(controls, workspace_id, payload.agent_id, config.enabled)
        if assessment["decision"] != "ALLOW":
            _error(403, "MODEL_PILOT_DENIED", decision=assessment)
        self.initialize_workspace(workspace_id)
        request_dict = payload.model_dump(mode="json")
        fingerprint = _hash(_json({"kind": "MODEL_PILOT", "payload": request_dict}))
        with self._connect(workspace_id, initialize=True) as con:
            existing = con.execute("SELECT * FROM agent_preparations WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing is not None:
                if existing["payload_fingerprint"] != fingerprint:
                    _error(409, "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")
                return self._preparation_view(existing), True
            generated = generate_local_draft(config, payload.objective, payload.source_summary, payload.evidence_references)
            preparation_id = "LMP-" + uuid.uuid4().hex[:20].upper()
            now = _utc_now()
            output = {
                "kind": "LOCAL_MODEL_RUNBOOK_DRAFT",
                "objective": payload.objective,
                "draft": generated,
                "execution_state": "NOT_EXECUTED",
                "model_execution": "LOCAL_OLLAMA_PILOT",
                "pilot_execution": "COMPLETED_FOR_HUMAN_REVIEW",
                "human_review_required": True,
                "tool_execution": "NONE",
                "shell_execution": "NONE",
                "git_write": "NONE",
                "database_write": "NONE",
                "deployment": "NONE",
                "external_network": "NONE",
                "cross_workspace_access": "DENY",
                "memory_write": "NONE",
            }
            input_hash = _hash(_json(request_dict))
            output_hash = _hash(_json(output))
            con.execute("""INSERT INTO agent_preparations(preparation_id,idempotency_key,payload_fingerprint,workspace_id,agent_id,policy_snapshot_json,request_json,output_json,preparation_state,execution_state,model_execution,pilot_execution,requested_by,created_at,completed_at,input_hash,output_hash)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (preparation_id, idempotency_key, fingerprint, workspace_id, payload.agent_id, _json({**controls, "model_pilot": assessment}), _json(request_dict), _json(output), "MODEL_DRAFT_PREPARED_FOR_HUMAN_REVIEW", "NOT_EXECUTED", "LOCAL_OLLAMA_PILOT", "COMPLETED_FOR_HUMAN_REVIEW", payload.requested_by, now, now, input_hash, output_hash))
            packet = {
                "workspace_id": workspace_id,
                "preparation_id": preparation_id,
                "agent_id": payload.agent_id,
                "execution_state": "NOT_EXECUTED",
                "model_execution": "LOCAL_OLLAMA_PILOT",
                "pilot_execution": "COMPLETED_FOR_HUMAN_REVIEW",
                "evidence_references": payload.evidence_references,
                "review_prompts": ["Confirm the result is a planning draft only.", "Confirm no tool or system execution is authorized.", "Confirm evidence scope before any human decision."],
                "approval_effect": "NO_EXECUTION_AUTHORITY_GRANTED",
            }
            packet_id = "LRP-" + uuid.uuid4().hex[:20].upper()
            packet_hash = _hash(_json(packet))
            con.execute("INSERT INTO review_packets(review_packet_id,preparation_id,workspace_id,packet_json,created_at,packet_hash) VALUES(?,?,?,?,?,?)", (packet_id, preparation_id, workspace_id, _json(packet), now, packet_hash))
            self._audit(con, preparation_id, "LOCAL_MODEL_PILOT_DRAFT_PREPARED", {"agent_id": payload.agent_id, "model": generated["model"], "execution_state": "NOT_EXECUTED", "model_execution": "LOCAL_OLLAMA_PILOT", "pilot_execution": "COMPLETED_FOR_HUMAN_REVIEW", "output_hash": output_hash, "review_packet_id": packet_id})
            row = con.execute("SELECT * FROM agent_preparations WHERE preparation_id=?", (preparation_id,)).fetchone()
        return self._preparation_view(row), False

    def list_preparations(self, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
        self._workspace(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None:
            return []
        with con:
            rows = con.execute("SELECT * FROM agent_preparations ORDER BY created_at DESC LIMIT ?", (min(max(limit, 1), 250),)).fetchall()
        return [self._preparation_view(row) for row in rows]

    def get_preparation(self, workspace_id: str, preparation_id: str) -> dict[str, Any]:
        self._workspace(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None:
            _error(404, "LOCAL_AGENT_PREPARATION_NOT_FOUND", preparation_id=preparation_id)
        with con:
            row = con.execute("SELECT * FROM agent_preparations WHERE preparation_id=?", (preparation_id,)).fetchone()
        if row is None:
            _error(404, "LOCAL_AGENT_PREPARATION_NOT_FOUND", preparation_id=preparation_id)
        return self._preparation_view(row)

    def list_review_packets(self, workspace_id: str) -> list[dict[str, Any]]:
        self._workspace(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None:
            return []
        with con:
            rows = con.execute("SELECT * FROM review_packets ORDER BY created_at DESC").fetchall()
        return [{"review_packet_id": row["review_packet_id"], "workspace_id": row["workspace_id"], "preparation_id": row["preparation_id"], "packet": _decode(row["packet_json"], {}), "created_at": row["created_at"], "packet_hash": row["packet_hash"]} for row in rows]

    def audit_integrity(self, workspace_id: str) -> dict[str, Any]:
        self._workspace(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None:
            return {"workspace_id": workspace_id, "audit_chain_integrity": "NO_LOCAL_AGENT_PREPARATIONS_YET", "event_count": 0, "failures": []}
        with con:
            rows = con.execute("SELECT * FROM audit_events ORDER BY sequence_no ASC").fetchall()
        previous_hash = None; failures: list[str] = []
        for row in rows:
            payload = _decode(row["payload_json"], {})
            expected = _hash(_json({"audit_id": row["audit_id"], "preparation_id": row["preparation_id"], "event_type": row["event_type"], "occurred_at": row["occurred_at"], "payload": payload, "previous_hash": previous_hash}))
            if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
                failures.append(row["audit_id"])
            previous_hash = row["event_hash"]
        return {"workspace_id": workspace_id, "audit_chain_integrity": "PASS" if not failures else "FAIL", "event_count": len(rows), "failures": failures}
