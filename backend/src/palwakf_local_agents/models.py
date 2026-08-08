from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class AgentSummary(BaseModel):
    id: str
    name_ar: str
    lifecycle: str
    authority: str


class TaskCreate(BaseModel):
    title: str = Field(min_length=8, max_length=180)
    system_scope: str = Field(min_length=2, max_length=80)
    request: str = Field(min_length=15, max_length=5000)
    risk_level: Literal['low', 'medium', 'high']
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requested_roles: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)


class TaskRecord(TaskCreate):
    id: str
    status: Literal['inbox', 'approved', 'rejected', 'needs_human_review']
    created_at: str


class HealthResponse(BaseModel):
    service: str
    bind_scope: str
    agent_execution_enabled: bool
    platform_mutation_enabled: bool
    database_access_enabled: bool
    safety_ok: bool
    timestamp: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
