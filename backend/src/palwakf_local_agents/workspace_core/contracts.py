from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceSummary(BaseModel):
    workspace_id: str
    display_name: str
    classification: str
    policy_pack_id: str
    policy_version: str
    lifecycle_state: str
    execution_mode: str
    legacy_data_migration: str


class PolicyPackSummary(BaseModel):
    policy_pack_id: str
    version: str
    classification: str
    model_execution: str
    pilot_execution: str
    external_integrations: str
    human_review: str
