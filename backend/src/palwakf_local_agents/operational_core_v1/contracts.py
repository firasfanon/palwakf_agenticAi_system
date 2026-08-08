from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GoalPrepareRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    project_type: str = Field(default="full_stack", min_length=2, max_length=80)
    target_user: str = Field(default="internal_user", min_length=2, max_length=160)
    priority: Literal["low", "normal", "high"] = "normal"
    constraints: list[str] = Field(default_factory=list, max_length=20)


class TaskTransitionRequest(BaseModel):
    action: Literal["ready_for_review", "accepted_as_plan", "returned_to_draft"]
    note: str | None = Field(default=None, max_length=500)


class ToolInvokeRequest(BaseModel):
    path: str | None = Field(default=None, max_length=260)
    limit: int = Field(default=100, ge=1, le=500)


class StandingRuleUpsertRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    statement: str = Field(min_length=3, max_length=1000)
    category: str = Field(default="engineering", min_length=2, max_length=80)
    enabled: bool = True


class InnovationReviewPrepareRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    context: str = Field(min_length=3, max_length=2000)
    focus: Literal["general", "architecture", "product_value", "ux", "performance", "security"] = "general"
    constraints: list[str] = Field(default_factory=list, max_length=20)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class ContextCheckRequest(BaseModel):
    proposed_action: str = Field(min_length=3, max_length=1200)
    declared_goal: str | None = Field(default=None, max_length=800)
    referenced_task_id: str | None = Field(default=None, max_length=120)


class AttemptRegisterRequest(BaseModel):
    operation_key: str = Field(pattern=r"^[A-Za-z0-9_.:-]{2,120}$")
    fingerprint: str = Field(min_length=2, max_length=240)
    outcome: Literal["success", "failure", "cancelled", "prepared_only"]
    note: str | None = Field(default=None, max_length=500)


class CheckpointCreateRequest(BaseModel):
    label: str = Field(min_length=2, max_length=160)
    reason: str = Field(min_length=2, max_length=600)
    include_task_statuses: bool = True


class ProjectIdentityRequest(BaseModel):
    project_name: str = Field(min_length=2, max_length=160)
    domain: str = Field(min_length=2, max_length=120)
    target_audience: str = Field(min_length=2, max_length=300)
    brand_personality: list[str] = Field(min_length=1, max_length=6)
    visual_keywords: list[str] = Field(default_factory=list, max_length=10)
    color_direction: str = Field(min_length=2, max_length=180)
    typography_direction: str = Field(min_length=2, max_length=180)
    density: Literal["compact", "balanced", "spacious"] = "balanced"
    motion_level: Literal["none", "subtle", "moderate"] = "subtle"
    accessibility_level: Literal["standard", "enhanced", "strict"] = "enhanced"
    text_direction: Literal["rtl", "ltr", "bilingual"] = "rtl"
    navigation_style: str = Field(min_length=2, max_length=180)
    card_style: str = Field(min_length=2, max_length=180)
    corner_style: str = Field(min_length=2, max_length=120)
    layout_signature: str = Field(min_length=2, max_length=240)
    distinctive_traits: list[str] = Field(default_factory=list, max_length=12)


class ProjectIdentitySimilarityRequest(ProjectIdentityRequest):
    project_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{1,79}$")
