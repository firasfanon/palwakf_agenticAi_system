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

from .contracts import EvidenceCreate, GovernedTaskCreate, ReviewRequest, TransitionRequest

SCHEMA_VERSION = "GOVERNED_OPERATIONS_WORKSPACE_SCOPING_V1"
_TASK_PREFIX = "GWS-"
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"inbox", "archived"},
    "inbox": {"under_review", "archived"},
    "under_review": {"approved", "rejected", "returned"},
    "returned": {"inbox", "archived"},
    "approved": {"archived"},
    "rejected": {"archived"},
    "archived": set(),
}
_DISPLAY_STATUS = {
    "official": "رسمي", "verified": "متحقق", "working": "قيد المراجعة", "unverified": "غير متحقق",
}


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


def _task_id(value: str) -> str:
    if not value.startswith(_TASK_PREFIX) or len(value) > 48:
        _error(404, "INVALID_WORKSPACE_GOVERNED_TASK_ID")
    return value


@dataclass(frozen=True)
class WorkspaceGovernedOperationsStore:
    project_root: Path

    @property
    def workspace_core(self) -> WorkspaceCoreStore:
        return WorkspaceCoreStore(self.project_root)

    def workspace_summary(self, workspace_id: str) -> dict[str, Any]:
        try:
            return self.workspace_core.workspace(validate_identifier(workspace_id, "workspace"))
        except KeyError:
            _error(404, "WORKSPACE_NOT_FOUND")
        except ValueError as error:
            _error(400, str(error))
        raise AssertionError("unreachable")

    def workspace_policy(self, workspace_id: str) -> dict[str, Any]:
        self.workspace_summary(workspace_id)
        try:
            return self.workspace_core.policy(workspace_id)
        except KeyError:
            _error(404, "WORKSPACE_NOT_FOUND")
        raise AssertionError("unreachable")

    def db_path(self, workspace_id: str) -> Path:
        workspace_id = validate_identifier(workspace_id, "workspace")
        root = (self.project_root / "workspaces" / workspace_id).resolve()
        parent = (self.project_root / "workspaces").resolve()
        if parent not in root.parents:
            _error(400, "CROSS_WORKSPACE_PATH_REJECTED")
        return root / "governed_operations.sqlite"

    def _connect(self, workspace_id: str, *, initialize: bool) -> sqlite3.Connection | None:
        path = self.db_path(workspace_id)
        if not path.exists() and not initialize:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _permission_intersection(self, workspace_id: str, requested_roles: list[str] | None = None) -> dict[str, Any]:
        workspace = self.workspace_summary(workspace_id)
        policy = self.workspace_policy(workspace_id)
        requested_roles = sorted({str(item).strip() for item in (requested_roles or []) if str(item).strip()})
        return {
            "workspace_id": workspace["workspace_id"],
            "policy_pack_id": policy["policy_pack_id"],
            "policy_version": policy["version"],
            "workspace_lifecycle_state": workspace["lifecycle_state"],
            "operation_scope": "LOCAL_GOVERNED_TASK_LIFECYCLE_ONLY",
            "agent_profile": "L0_READ_ONLY_BASELINE",
            "requested_roles": requested_roles,
            "permitted_roles": [role for role in requested_roles if role in {"coordinator", "sovereignty_reviewer", "documentation_handoff", "knowledge_researcher"}],
            "execution_gateway": "DISABLED_BY_DEFAULT",
            "model_execution": "NONE",
            "pilot_execution": "NOT_EXECUTED",
            "tool_execution": "NONE",
            "external_network": "NONE",
            "platform_mutation": "NONE",
            "cross_workspace_read": "DENY",
            "cross_workspace_write": "DENY",
            "memory_write": "NONE",
            "approval_is_execution": "FALSE",
            "human_review": policy["review"]["human_review"],
            "policy_hash": _hash(_json(policy)),
        }

    def initialize_workspace(self, workspace_id: str) -> None:
        workspace = self.workspace_summary(workspace_id)
        policy = self.workspace_policy(workspace_id)
        with self._connect(workspace_id, initialize=True) as con:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            con.execute("""
                CREATE TABLE IF NOT EXISTS governed_tasks (
                    task_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_fingerprint TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    policy_pack_id TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    permission_snapshot_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    request TEXT NOT NULL,
                    system_scope TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    requested_roles_json TEXT NOT NULL,
                    allowed_paths_json TEXT NOT NULL,
                    forbidden_actions_json TEXT NOT NULL,
                    evidence_required_json TEXT NOT NULL,
                    execution_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS task_transition_events (
                    event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL,
                    actor_id TEXT NOT NULL, rationale TEXT NOT NULL, evidence_ids_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES governed_tasks(task_id)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS human_reviews (
                    review_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, decision TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL, rationale TEXT NOT NULL, evidence_ids_json TEXT NOT NULL,
                    created_at TEXT NOT NULL, event_hash TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES governed_tasks(task_id)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_id TEXT PRIMARY KEY, task_id TEXT, category TEXT NOT NULL, source_type TEXT NOT NULL,
                    trust_level TEXT NOT NULL, raw_status TEXT NOT NULL, display_status TEXT NOT NULL,
                    summary TEXT NOT NULL, source_reference TEXT NOT NULL, metadata_json TEXT NOT NULL,
                    created_by TEXT NOT NULL, created_at TEXT NOT NULL, content_hash TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES governed_tasks(task_id)
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence_no INTEGER PRIMARY KEY AUTOINCREMENT, audit_id TEXT NOT NULL UNIQUE, task_id TEXT,
                    event_type TEXT NOT NULL, actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL, previous_hash TEXT, event_hash TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES governed_tasks(task_id)
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_workspace_task_status ON governed_tasks(status, updated_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_workspace_evidence_task ON evidence_records(task_id, created_at DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_workspace_audit_sequence ON audit_events(sequence_no ASC)")
            con.execute("INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)", (SCHEMA_VERSION, _utc_now()))
            existing = con.execute("SELECT 1 FROM audit_events WHERE event_type='WORKSPACE_OPERATIONS_BOUND' LIMIT 1").fetchone()
            if existing is None:
                self._audit(con, None, "WORKSPACE_OPERATIONS_BOUND", "system", {
                    "workspace_id": workspace["workspace_id"], "policy_pack_id": policy["policy_pack_id"],
                    "policy_version": policy["version"], "scope": "LOCAL_GOVERNED_TASK_LIFECYCLE_ONLY",
                })

    def _audit(self, con: sqlite3.Connection, task_id: str | None, event_type: str, actor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prior = con.execute("SELECT event_hash FROM audit_events ORDER BY sequence_no DESC LIMIT 1").fetchone()
        previous_hash = prior["event_hash"] if prior else None
        occurred_at = _utc_now()
        audit_id = "GWA-" + _hash(f"{task_id}|{event_type}|{actor_id}|{occurred_at}|{_json(payload)}")[:18]
        record = {"audit_id": audit_id, "task_id": task_id, "event_type": event_type, "actor_id": actor_id,
                  "occurred_at": occurred_at, "payload": payload, "previous_hash": previous_hash}
        event_hash = _hash(_json(record))
        con.execute("INSERT INTO audit_events(audit_id,task_id,event_type,actor_id,occurred_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)",
                    (audit_id, task_id, event_type, actor_id, occurred_at, _json(payload), previous_hash, event_hash))
        return {**record, "event_hash": event_hash}

    def _row_task(self, con: sqlite3.Connection, task_id: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM governed_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            _error(404, "WORKSPACE_GOVERNED_TASK_NOT_FOUND", task_id=task_id)
        return row

    def _task_view(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "task_id": row["task_id"], "workspace_id": row["workspace_id"], "policy_pack_id": row["policy_pack_id"],
            "policy_version": row["policy_version"], "permission_intersection": _decode(row["permission_snapshot_json"], {}),
            "status": row["status"], "version": row["version"], "title": row["title"], "request": row["request"],
            "system_scope": row["system_scope"], "risk_level": row["risk_level"], "requested_by": row["requested_by"],
            "requested_roles": _decode(row["requested_roles_json"], []), "allowed_paths": _decode(row["allowed_paths_json"], []),
            "forbidden_actions": _decode(row["forbidden_actions_json"], []), "evidence_required": _decode(row["evidence_required_json"], []),
            "execution_state": row["execution_state"], "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def _evidence_view(self, row: sqlite3.Row) -> dict[str, Any]:
        return {"evidence_id": row["evidence_id"], "task_id": row["task_id"], "category": row["category"],
                "source_type": row["source_type"], "trust_level": row["trust_level"], "raw_status": row["raw_status"],
                "display_status": row["display_status"], "summary": row["summary"], "source_reference": row["source_reference"],
                "metadata": _decode(row["metadata_json"], {}), "created_by": row["created_by"], "created_at": row["created_at"],
                "content_hash": row["content_hash"]}

    def _required_evidence(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        required = _decode(row["evidence_required_json"], [])
        records = con.execute("SELECT category FROM evidence_records WHERE task_id=?", (row["task_id"],)).fetchall()
        present = {item["category"] for item in records}
        missing = [item for item in required if item not in present]
        return {"required_categories": required, "present_categories": sorted(present), "missing_categories": missing,
                "evidence_gate": "PASS" if not missing else "BLOCKED"}

    def workspace_status(self, workspace_id: str) -> dict[str, Any]:
        workspace = self.workspace_summary(workspace_id)
        policy = self.workspace_policy(workspace_id)
        exists = self.db_path(workspace_id).exists()
        return {
            "workspace_id": workspace["workspace_id"], "display_name": workspace["display_name"],
            "classification": workspace["classification"], "lifecycle_state": workspace["lifecycle_state"],
            "policy_pack_id": policy["policy_pack_id"], "policy_version": policy["version"],
            "workspace_operations_binding": "BOUND_LOCAL_STATE_ON_EXPLICIT_HUMAN_ACTION",
            "workspace_storage_initialized": exists,
            "task_storage_scope": f"workspaces/{workspace['workspace_id']}/governed_operations.sqlite",
            "legacy_governed_operations": "SEPARATE_NOT_MIGRATED",
            "permission_intersection": self._permission_intersection(workspace_id),
        }

    def list_workspace_statuses(self) -> list[dict[str, Any]]:
        return [self.workspace_status(item["workspace_id"]) for item in self.workspace_core.list_workspaces()]

    def controls(self, workspace_id: str) -> dict[str, Any]:
        status = self.workspace_status(workspace_id)
        return {**status["permission_intersection"], "workspace_operations_binding": status["workspace_operations_binding"],
                "local_persistent_state": "WORKSPACE_LOCAL_SQLITE_ON_EXPLICIT_HUMAN_ACTION",
                "execution_notice": "NO_EXECUTE_OR_DISPATCH_ROUTE_EXISTS"}

    def health(self) -> dict[str, Any]:
        statuses = self.list_workspace_statuses()
        return {
            "health": "GOVERNED_OPERATIONS_WORKSPACE_SCOPING_READY",
            "workspace_scope_required": "YES", "workspace_count": len(statuses),
            "bound_workspace_count": len(statuses), "cross_workspace_access": "DENY",
            "legacy_governed_operations": "SEPARATE_NOT_MIGRATED",
            "storage": "PER_WORKSPACE_LOCAL_SQLITE_ON_EXPLICIT_HUMAN_ACTION",
            "model_execution": "NONE", "pilot_execution": "NOT_EXECUTED", "platform_mutation": "NONE",
            "external_database_access": "NONE", "git_write": "NONE", "deployment": "NONE", "secrets_access": "NONE", "memory_write": "NONE",
        }

    def create_task(self, workspace_id: str, payload: GovernedTaskCreate, idempotency_key: str) -> tuple[dict[str, Any], bool]:
        workspace_id = validate_identifier(workspace_id, "workspace")
        if not idempotency_key or len(idempotency_key) > 160:
            _error(400, "IDEMPOTENCY_KEY_REQUIRED")
        self.initialize_workspace(workspace_id)
        intersection = self._permission_intersection(workspace_id, payload.requested_roles)
        fingerprint = _hash(_json(payload.model_dump(mode="json")))
        with self._connect(workspace_id, initialize=True) as con:
            existing = con.execute("SELECT * FROM governed_tasks WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing is not None:
                if existing["payload_fingerprint"] != fingerprint:
                    _error(409, "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH")
                return self._task_view(existing), True
            task_id = _TASK_PREFIX + uuid.uuid4().hex[:18].upper()
            now = _utc_now()
            con.execute("""INSERT INTO governed_tasks(task_id,idempotency_key,payload_fingerprint,workspace_id,policy_pack_id,policy_version,permission_snapshot_json,status,version,title,request,system_scope,risk_level,requested_by,requested_roles_json,allowed_paths_json,forbidden_actions_json,evidence_required_json,execution_state,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (task_id, idempotency_key, fingerprint, workspace_id, intersection["policy_pack_id"], intersection["policy_version"], _json(intersection),
                         "draft", 1, payload.title, payload.request, payload.system_scope, payload.risk_level, payload.requested_by,
                         _json(payload.requested_roles), _json(payload.allowed_paths), _json(payload.forbidden_actions), _json(payload.evidence_required),
                         "NOT_EXECUTED", now, now))
            row = self._row_task(con, task_id)
            self._audit(con, task_id, "TASK_DRAFT_CREATED", payload.requested_by, {"workspace_id": workspace_id, "risk_level": payload.risk_level,
                "policy_pack_id": intersection["policy_pack_id"], "permission_snapshot_hash": _hash(_json(intersection))})
            return self._task_view(row), False

    def list_tasks(self, workspace_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.workspace_summary(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None:
            return []
        with con:
            query = "SELECT * FROM governed_tasks"; params: list[Any] = []
            if status:
                query += " WHERE status=?"; params.append(status)
            query += " ORDER BY updated_at DESC LIMIT ?"; params.append(min(max(limit, 1), 250))
            rows = con.execute(query, params).fetchall()
        return [self._task_view(row) for row in rows]

    def get_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        _task_id(task_id); self.workspace_summary(workspace_id)
        con = self._connect(workspace_id, initialize=False)
        if con is None: _error(404, "WORKSPACE_GOVERNED_TASK_NOT_FOUND", task_id=task_id)
        with con:
            row = self._row_task(con, task_id)
        return self._task_view(row)

    def list_history(self, workspace_id: str, task_id: str) -> list[dict[str, Any]]:
        _task_id(task_id); con = self._connect(workspace_id, initialize=False)
        if con is None: _error(404, "WORKSPACE_GOVERNED_TASK_NOT_FOUND", task_id=task_id)
        with con:
            self._row_task(con, task_id)
            rows = con.execute("SELECT * FROM task_transition_events WHERE task_id=? ORDER BY occurred_at ASC", (task_id,)).fetchall()
        return [{"event_id": row["event_id"], "task_id": row["task_id"], "from_status": row["from_status"], "to_status": row["to_status"],
                 "actor_id": row["actor_id"], "rationale": row["rationale"], "evidence_ids": _decode(row["evidence_ids_json"], []),
                 "occurred_at": row["occurred_at"], "previous_hash": row["previous_hash"], "event_hash": row["event_hash"]} for row in rows]

    def list_reviews(self, workspace_id: str, task_id: str | None = None) -> list[dict[str, Any]]:
        con = self._connect(workspace_id, initialize=False)
        if con is None: return []
        with con:
            if task_id: self._row_task(con, task_id); rows = con.execute("SELECT * FROM human_reviews WHERE task_id=? ORDER BY created_at DESC", (task_id,)).fetchall()
            else: rows = con.execute("SELECT * FROM human_reviews ORDER BY created_at DESC").fetchall()
        return [{"review_id": row["review_id"], "task_id": row["task_id"], "decision": row["decision"], "reviewer_id": row["reviewer_id"],
                 "rationale": row["rationale"], "evidence_ids": _decode(row["evidence_ids_json"], []), "created_at": row["created_at"], "event_hash": row["event_hash"]} for row in rows]

    def list_evidence(self, workspace_id: str, task_id: str | None = None) -> list[dict[str, Any]]:
        con = self._connect(workspace_id, initialize=False)
        if con is None: return []
        with con:
            if task_id: self._row_task(con, task_id); rows = con.execute("SELECT * FROM evidence_records WHERE task_id=? ORDER BY created_at DESC", (task_id,)).fetchall()
            else: rows = con.execute("SELECT * FROM evidence_records ORDER BY created_at DESC").fetchall()
        return [self._evidence_view(row) for row in rows]

    def add_evidence(self, workspace_id: str, payload: EvidenceCreate) -> dict[str, Any]:
        self.initialize_workspace(workspace_id)
        with self._connect(workspace_id, initialize=True) as con:
            if payload.task_id: self._row_task(con, _task_id(payload.task_id))
            evidence_id = "GWE-" + uuid.uuid4().hex[:18].upper(); now = _utc_now()
            metadata = {**payload.metadata, "workspace_id": workspace_id, "scope_contract": "NO_CROSS_WORKSPACE_READ_WRITE"}
            content_hash = _hash(_json({"workspace_id": workspace_id, "task_id": payload.task_id, "category": payload.category, "source_type": payload.source_type,
                "trust_level": payload.trust_level, "raw_status": payload.raw_status, "summary": payload.summary, "source_reference": payload.source_reference, "metadata": metadata}))
            con.execute("INSERT INTO evidence_records(evidence_id,task_id,category,source_type,trust_level,raw_status,display_status,summary,source_reference,metadata_json,created_by,created_at,content_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (evidence_id, payload.task_id, payload.category, payload.source_type, payload.trust_level, payload.raw_status, _DISPLAY_STATUS[payload.trust_level], payload.summary, payload.source_reference, _json(metadata), payload.actor_id, now, content_hash))
            row = con.execute("SELECT * FROM evidence_records WHERE evidence_id=?", (evidence_id,)).fetchone()
            self._audit(con, payload.task_id, "EVIDENCE_RECORDED", payload.actor_id, {"workspace_id": workspace_id, "evidence_id": evidence_id, "category": payload.category, "trust_level": payload.trust_level})
            return self._evidence_view(row)

    def _record_transition(self, con: sqlite3.Connection, row: sqlite3.Row, destination: str, payload: TransitionRequest) -> dict[str, Any]:
        current = row["status"]
        if destination not in _ALLOWED_TRANSITIONS.get(current, set()): _error(409, "INVALID_TASK_TRANSITION", from_status=current, to_status=destination)
        if payload.expected_version != row["version"]: _error(409, "TASK_VERSION_CONFLICT", expected=row["version"], received=payload.expected_version)
        prior = con.execute("SELECT event_hash FROM task_transition_events WHERE task_id=? ORDER BY occurred_at DESC LIMIT 1", (row["task_id"],)).fetchone()
        previous_hash = prior["event_hash"] if prior else None; occurred_at = _utc_now(); event_id = "GWT-" + uuid.uuid4().hex[:18].upper()
        record = {"event_id": event_id, "task_id": row["task_id"], "from_status": current, "to_status": destination, "actor_id": payload.actor_id,
                  "rationale": payload.rationale, "evidence_ids": payload.evidence_ids, "occurred_at": occurred_at, "previous_hash": previous_hash}
        event_hash = _hash(_json(record))
        con.execute("INSERT INTO task_transition_events(event_id,task_id,from_status,to_status,actor_id,rationale,evidence_ids_json,occurred_at,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (event_id, row["task_id"], current, destination, payload.actor_id, payload.rationale, _json(payload.evidence_ids), occurred_at, previous_hash, event_hash))
        con.execute("UPDATE governed_tasks SET status=?,version=?,updated_at=? WHERE task_id=?", (destination, row["version"] + 1, occurred_at, row["task_id"]))
        updated = self._row_task(con, row["task_id"])
        self._audit(con, row["task_id"], "TASK_TRANSITION", payload.actor_id, {"from_status": current, "to_status": destination, "event_id": event_id, "workspace_id": updated["workspace_id"]})
        return self._task_view(updated)

    def transition(self, workspace_id: str, task_id: str, destination: str, payload: TransitionRequest) -> dict[str, Any]:
        self.initialize_workspace(workspace_id)
        with self._connect(workspace_id, initialize=True) as con:
            row = self._row_task(con, _task_id(task_id))
            return {"task": self._record_transition(con, row, destination, payload), "execution_notice": "NO_EXECUTE_OR_DISPATCH_ROUTE_EXISTS"}

    def review(self, workspace_id: str, task_id: str, payload: ReviewRequest) -> dict[str, Any]:
        self.initialize_workspace(workspace_id)
        with self._connect(workspace_id, initialize=True) as con:
            row = self._row_task(con, _task_id(task_id))
            if row["status"] != "under_review": _error(409, "REVIEW_REQUIRES_UNDER_REVIEW")
            if payload.expected_version != row["version"]: _error(409, "TASK_VERSION_CONFLICT", expected=row["version"], received=payload.expected_version)
            if payload.decision == "approve":
                readiness = self._required_evidence(con, row)
                if readiness["missing_categories"]: _error(409, "APPROVAL_EVIDENCE_GATE_BLOCKED", **readiness)
            task = self._record_transition(con, row, {"approve": "approved", "reject": "rejected", "return": "returned"}[payload.decision], payload)
            review_id = "GWR-" + uuid.uuid4().hex[:18].upper(); event_hash = _hash(_json({"review_id": review_id, "task_id": task_id, "decision": payload.decision, "reviewer_id": payload.actor_id, "rationale": payload.rationale, "evidence_ids": payload.evidence_ids, "workspace_id": workspace_id}))
            con.execute("INSERT INTO human_reviews(review_id,task_id,decision,reviewer_id,rationale,evidence_ids_json,created_at,event_hash) VALUES(?,?,?,?,?,?,?,?)",
                        (review_id, task_id, payload.decision, payload.actor_id, payload.rationale, _json(payload.evidence_ids), _utc_now(), event_hash))
            self._audit(con, task_id, "HUMAN_REVIEW_RECORDED", payload.actor_id, {"review_id": review_id, "decision": payload.decision, "workspace_id": workspace_id, "attestation": payload.reviewer_attestation})
            return {"task": task, "review_id": review_id, "execution_notice": "APPROVAL_IS_NOT_EXECUTION"}

    def task_readiness(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        con = self._connect(workspace_id, initialize=False)
        if con is None: _error(404, "WORKSPACE_GOVERNED_TASK_NOT_FOUND", task_id=task_id)
        with con:
            row = self._row_task(con, _task_id(task_id)); readiness = self._required_evidence(con, row)
        return {"workspace_id": workspace_id, "task_id": task_id, "status": row["status"], "version": row["version"], "execution_state": "NOT_EXECUTED", "human_review_required": "YES", **readiness}

    def task_integrity(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        history = self.list_history(workspace_id, task_id); previous = None; failures: list[dict[str, Any]] = []
        for item in history:
            expected = _hash(_json({key: item[key] for key in ("event_id", "task_id", "from_status", "to_status", "actor_id", "rationale", "evidence_ids", "occurred_at", "previous_hash")}))
            if item["previous_hash"] != previous: failures.append({"event_id": item["event_id"], "code": "PREVIOUS_HASH_MISMATCH"})
            if item["event_hash"] != expected: failures.append({"event_id": item["event_id"], "code": "EVENT_HASH_MISMATCH"})
            previous = item["event_hash"]
        return {"workspace_id": workspace_id, "task_id": task_id, "event_count": len(history), "integrity": "PASS" if not failures else "FAIL", "failures": failures, "terminal_hash": previous}

    def audit_integrity(self, workspace_id: str) -> dict[str, Any]:
        con = self._connect(workspace_id, initialize=False)
        if con is None: return {"workspace_id": workspace_id, "audit_chain_integrity": "PASS", "audit_event_count": 0, "terminal_hash": None, "failures": []}
        with con: rows = con.execute("SELECT * FROM audit_events ORDER BY sequence_no ASC").fetchall()
        previous = None; failures: list[dict[str, Any]] = []
        for row in rows:
            record = {"audit_id": row["audit_id"], "task_id": row["task_id"], "event_type": row["event_type"], "actor_id": row["actor_id"], "occurred_at": row["occurred_at"], "payload": _decode(row["payload_json"], {}), "previous_hash": row["previous_hash"]}
            if row["previous_hash"] != previous: failures.append({"sequence_no": row["sequence_no"], "code": "PREVIOUS_HASH_MISMATCH"})
            if row["event_hash"] != _hash(_json(record)): failures.append({"sequence_no": row["sequence_no"], "code": "EVENT_HASH_MISMATCH"})
            previous = row["event_hash"]
        return {"workspace_id": workspace_id, "audit_chain_integrity": "PASS" if not failures else "FAIL", "audit_event_count": len(rows), "terminal_hash": previous, "failures": failures}

    def task_bundle(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        return {"workspace": self.workspace_status(workspace_id), "task": self.get_task(workspace_id, task_id),
                "history": self.list_history(workspace_id, task_id), "evidence": self.list_evidence(workspace_id, task_id),
                "reviews": self.list_reviews(workspace_id, task_id), "readiness": self.task_readiness(workspace_id, task_id),
                "integrity": self.task_integrity(workspace_id, task_id), "execution_notice": "NO_EXECUTE_OR_DISPATCH_ROUTE_EXISTS"}

    def summary(self, workspace_id: str) -> dict[str, Any]:
        tasks = self.list_tasks(workspace_id, limit=250); counts = {status: 0 for status in _ALLOWED_TRANSITIONS}
        for task in tasks: counts[task["status"]] = counts.get(task["status"], 0) + 1
        return {"workspace": self.workspace_status(workspace_id), "counts": counts, "tasks": tasks[:12], "recent_reviews": self.list_reviews(workspace_id)[:8],
                "recent_evidence": self.list_evidence(workspace_id)[:12], "integrity": self.audit_integrity(workspace_id), "controls": self.controls(workspace_id)}
