from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any
from .models import TaskCreate, TaskRecord, utc_now

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / 'audit' / 'local_agents.sqlite'


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def initialize() -> None:
    with _connect() as con:
        con.execute('''
            create table if not exists tasks (
                id text primary key,
                created_at text not null,
                status text not null,
                title text not null,
                system_scope text not null,
                risk_level text not null,
                payload_json text not null
            )
        ''')
        con.execute('''
            create table if not exists audit_events (
                id integer primary key autoincrement,
                created_at text not null,
                event_type text not null,
                detail_json text not null
            )
        ''')


def create_task(payload: TaskCreate) -> TaskRecord:
    task_id = f'TASK-{uuid.uuid4().hex[:12].upper()}'
    created_at = utc_now()
    record = TaskRecord(id=task_id, status='inbox', created_at=created_at, **payload.model_dump())
    with _connect() as con:
        con.execute(
            'insert into tasks(id, created_at, status, title, system_scope, risk_level, payload_json) values(?,?,?,?,?,?,?)',
            (task_id, created_at, 'inbox', record.title, record.system_scope, record.risk_level, json.dumps(record.model_dump(), ensure_ascii=False)),
        )
        con.execute(
            'insert into audit_events(created_at, event_type, detail_json) values(?,?,?)',
            (created_at, 'task_created', json.dumps({'task_id': task_id, 'status': 'inbox'}, ensure_ascii=False)),
        )
    return record


def list_tasks() -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute('select payload_json from tasks order by created_at desc').fetchall()
    return [json.loads(row['payload_json']) for row in rows]


def list_audit(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute(
            'select id, created_at, event_type, detail_json from audit_events order by id desc limit ?', (limit,)
        ).fetchall()
    return [
        {'id': row['id'], 'created_at': row['created_at'], 'event_type': row['event_type'], 'detail': json.loads(row['detail_json'])}
        for row in rows
    ]
