from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


CoreAgentOperatingModel = Literal["CORE_AGENT_OPERATING_MODEL_V1"]
AgentOutputAuthority = Literal["PROPOSAL_ONLY_NO_EXECUTION"]
TaskBindingState = Literal["TASK_ID_BOUND", "TASK_ID_NOT_SUPPLIED_PREPARE_ONLY"]


AgentId = Literal[
    "policy_guardian_agent_v1",
    "local_agent_coordinator_v1",
    "evidence_audit_agent_v1",
    "repository_test_triage_agent_v1",
    "task_planning_runbook_agent_v1",
    "human_review_copilot_v1",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentPreparationCreate(_StrictModel):
    agent_id: AgentId
    task_id: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        description="Optional governed task identifier. Required before any future operational activation or execution authority.",
    )
    objective: str = Field(min_length=12, max_length=8000)
    requested_by: str = Field(min_length=3, max_length=64)
    requested_capabilities: list[str] = Field(default_factory=list, max_length=12)
    source_summary: str = Field(default="", max_length=12000)
    evidence_references: list[str] = Field(default_factory=list, max_length=24)


    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        allowed = cleaned.replace("_", "").replace("-", "").replace(".", "").replace(":", "")
        if not allowed.isalnum():
            raise ValueError("task_id must use letters, digits, underscore, dash, dot, or colon")
        return cleaned

    @field_validator("requested_by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        value = value.strip()
        if not value.replace("_", "").replace("-", "").replace(".", "").isalnum():
            raise ValueError("requested_by must use letters, digits, underscore, dash, or dot")
        return value

    @field_validator("requested_capabilities")
    @classmethod
    def normalize_capabilities(cls, value: list[str]) -> list[str]:
        return sorted({item.strip().lower() for item in value if item.strip()})


class ModelPilotDraftCreate(_StrictModel):
    agent_id: Literal["task_planning_runbook_agent_v1"]
    objective: str = Field(min_length=12, max_length=8000)
    requested_by: str = Field(min_length=3, max_length=64)
    source_summary: str = Field(default="", max_length=12000)
    evidence_references: list[str] = Field(default_factory=list, max_length=24)

    @field_validator("requested_by")
    @classmethod
    def validate_model_pilot_actor(cls, value: str) -> str:
        return AgentPreparationCreate.validate_actor(value)
