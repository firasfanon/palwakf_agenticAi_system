from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskStatus = Literal["draft", "inbox", "under_review", "approved", "rejected", "returned", "archived"]
Decision = Literal["approve", "reject", "return"]
TrustLevel = Literal["official", "verified", "working", "unverified"]
RiskLevel = Literal["low", "medium", "high", "critical"]


def _validate_actor(value: str) -> str:
    cleaned = value.strip()
    if not cleaned.replace("_", "").replace("-", "").replace(".", "").isalnum():
        raise ValueError("actor id must use letters, digits, underscore, dash, or dot")
    return cleaned


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GovernedTaskCreate(_StrictModel):
    title: str = Field(min_length=8, max_length=180)
    request: str = Field(min_length=15, max_length=8000)
    system_scope: str = Field(min_length=2, max_length=100)
    risk_level: RiskLevel
    requested_by: str = Field(min_length=3, max_length=64)
    requested_roles: list[str] = Field(default_factory=list, max_length=12)
    allowed_paths: list[str] = Field(default_factory=list, max_length=30)
    forbidden_actions: list[str] = Field(default_factory=list, max_length=30)
    evidence_required: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("requested_by")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _validate_actor(value)


class TransitionRequest(_StrictModel):
    actor_id: str = Field(min_length=3, max_length=64)
    rationale: str = Field(min_length=12, max_length=4000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    expected_version: int = Field(ge=1)

    @field_validator("actor_id")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _validate_actor(value)


class ReviewRequest(TransitionRequest):
    decision: Decision
    reviewer_attestation: Literal["LOCAL_HUMAN_REVIEW_ASSERTED"]


class EvidenceCreate(_StrictModel):
    actor_id: str = Field(min_length=3, max_length=64)
    task_id: str | None = None
    category: str = Field(min_length=3, max_length=80)
    source_type: str = Field(min_length=3, max_length=80)
    trust_level: TrustLevel
    raw_status: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=3, max_length=4000)
    source_reference: str = Field(min_length=3, max_length=500)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("actor_id")
    @classmethod
    def validate_actor(cls, value: str) -> str:
        return _validate_actor(value)
