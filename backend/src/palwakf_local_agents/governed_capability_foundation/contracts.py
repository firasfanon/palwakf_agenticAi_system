from __future__ import annotations

from pydantic import BaseModel, Field


class _ScopedWrite(BaseModel):
    client_id: str | None = Field(default=None, max_length=120)


class TaskCreate(_ScopedWrite):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=12000)


class ProjectCreate(_ScopedWrite):
    name: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=12000)


class ReviewDecision(_ScopedWrite):
    subject_type: str = Field(pattern="^(task|project|tool_run|pilot)$")
    subject_id: str = Field(min_length=1, max_length=160)
    decision: str = Field(pattern="^(approved|rejected|needs_changes)$")
    rationale: str = Field(default="", max_length=12000)


class DeterministicToolRequest(_ScopedWrite):
    text: str = Field(min_length=1, max_length=24000)


class PilotExecutionRequest(BaseModel):
    workspace_id: str = Field(pattern="^research_learning$")
    prompt: str = Field(min_length=1, max_length=4000)
    human_reviewer: str = Field(min_length=1, max_length=120)
    explicit_execution_confirmation: bool = False
