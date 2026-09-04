from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .contracts import AuthorizationEnvelope, RunRequest, utc_now
from .learning import LearningCandidate


class WorkspaceStatePackage(BaseModel):
    state_package_id: str
    project_id: str
    task_id: str
    repository: str
    task_branch: str
    base_sha: str
    expected_head: str
    authorization: AuthorizationEnvelope
    authority_source: Literal["WORKSPACE_MANAGER", "HUMAN_EXPLICIT"]
    accepted_project_knowledge_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def bind_authority(self):
        if self.authorization.project_id != self.project_id:
            raise ValueError("STATE_PACKAGE_PROJECT_AUTHORITY_MISMATCH")
        if self.authorization.task_id != self.task_id:
            raise ValueError("STATE_PACKAGE_TASK_AUTHORITY_MISMATCH")
        if self.authorization.issuer != self.authority_source:
            raise ValueError("STATE_PACKAGE_ISSUER_MISMATCH")
        return self


class MindCandidateSubmission(BaseModel):
    submission_id: str = Field(default_factory=lambda: f"mind-sub-{uuid4()}")
    project_id: str
    task_id: str
    candidate_ids: list[str]
    knowledge_authority: Literal["EXTERNAL_MIND_WORKSPACE_REVIEW"] = "EXTERNAL_MIND_WORKSPACE_REVIEW"
    auto_promotion: Literal[False] = False
    created_at: str = Field(default_factory=utc_now)


class ExternalContractAdapter:
    def validate_workspace_package(self, package: WorkspaceStatePackage) -> WorkspaceStatePackage:
        if not package.task_branch.startswith("task/"):
            raise ValueError("WORKSPACE_TASK_BRANCH_REQUIRED")
        if package.authorization.allow_network_write:
            raise ValueError("WORKSPACE_NETWORK_WRITE_AUTHORITY_REJECTED")
        return package

    def validate_run_binding(
        self,
        *,
        package: WorkspaceStatePackage,
        request: RunRequest,
    ) -> None:
        if request.state_package_id != package.state_package_id:
            raise ValueError("RUN_STATE_PACKAGE_MISMATCH")
        if request.project_id != package.project_id or request.task_id != package.task_id:
            raise ValueError("RUN_STATE_PACKAGE_SCOPE_MISMATCH")
        if request.environment.repository != package.repository:
            raise ValueError("RUN_REPOSITORY_BINDING_MISMATCH")
        if request.environment.task_branch != package.task_branch:
            raise ValueError("RUN_TASK_BRANCH_BINDING_MISMATCH")
        if request.environment.base_sha != package.base_sha:
            raise ValueError("RUN_BASE_SHA_BINDING_MISMATCH")
        if request.environment.expected_head != package.expected_head:
            raise ValueError("RUN_EXPECTED_HEAD_BINDING_MISMATCH")
        if request.authorization != package.authorization:
            raise ValueError("RUN_AUTHORIZATION_BINDING_MISMATCH")

    def mind_submission(self, *, package: WorkspaceStatePackage, candidates: list[LearningCandidate]) -> MindCandidateSubmission:
        if any(c.project_id != package.project_id or c.task_id != package.task_id for c in candidates):
            raise ValueError("MIND_SUBMISSION_SCOPE_MISMATCH")
        return MindCandidateSubmission(project_id=package.project_id, task_id=package.task_id, candidate_ids=[c.candidate_id for c in candidates])
