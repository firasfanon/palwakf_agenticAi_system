from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .intersystem_v1 import (
    AgenticIntegrationPilotResultV1,
    WorkspaceAuthorityPackageV1,
    execute_integration_pilot,
)
from .learning_service import AgenticLearningService
from .runtime import AuthorityError

CONTRACT_ID = "PALWAKF_FOUR_SYSTEM_L4_OPERATIONAL_CONTRACT_V1"


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class FourSystemL4ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: Literal["PALWAKF_FOUR_SYSTEM_L4_OPERATIONAL_CONTRACT_V1"] = CONTRACT_ID
    workspace_run_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=200)
    authority_package: WorkspaceAuthorityPackageV1


class FourSystemL4ExecutionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: Literal["PALWAKF_FOUR_SYSTEM_L4_OPERATIONAL_CONTRACT_V1"] = CONTRACT_ID
    workspace_run_id: str
    correlation_id: str
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    agentic_result: AgenticIntegrationPilotResultV1
    resume_token: str


class AgenticL4JournalRecord(BaseModel):
    workspace_run_id: str
    correlation_id: str
    request_sha256: str
    status: Literal["STARTED", "COMPLETED", "FAIL_CLOSED"]
    result: dict | None = None
    error: str | None = None


class AgenticL4Journal:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (
            root
            or Path(
                os.getenv(
                    "PALWAKF_AGENTIC_L4_STATE_ROOT",
                    str(Path(tempfile.gettempdir()) / "palwakf_agentic_l4_state"),
                )
            )
        ).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, workspace_run_id: str) -> Path:
        safe = hashlib.sha256(workspace_run_id.encode("utf-8")).hexdigest()
        return self.root / f"{safe}.json"

    def load(self, workspace_run_id: str) -> AgenticL4JournalRecord | None:
        path = self._path(workspace_run_id)
        if not path.exists():
            return None
        return AgenticL4JournalRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: AgenticL4JournalRecord) -> None:
        path = self._path(record.workspace_run_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        temp.replace(path)


class FourSystemL4AgenticService:
    def __init__(
        self,
        *,
        journal: AgenticL4Journal,
        executor: Callable[[WorkspaceAuthorityPackageV1], AgenticIntegrationPilotResultV1],
    ) -> None:
        self.journal = journal
        self.executor = executor

    def execute(self, request: FourSystemL4ExecutionRequest) -> FourSystemL4ExecutionEnvelope:
        request_payload = request.model_dump(mode="json")
        request_sha = _sha(request_payload)
        existing = self.journal.load(request.workspace_run_id)

        if existing is not None:
            if (
                existing.correlation_id != request.correlation_id
                or existing.request_sha256 != request_sha
            ):
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_IDEMPOTENCY_CONFLICT")
            if existing.status == "COMPLETED" and existing.result is not None:
                return FourSystemL4ExecutionEnvelope.model_validate(existing.result)
            raise ValueError("FOUR_SYSTEM_L4_AGENTIC_INCOMPLETE_PREVIOUS_ATTEMPT_REQUIRES_REVIEW")

        self.journal.save(
            AgenticL4JournalRecord(
                workspace_run_id=request.workspace_run_id,
                correlation_id=request.correlation_id,
                request_sha256=request_sha,
                status="STARTED",
            )
        )

        try:
            result = self.executor(request.authority_package)
            result_dict = result.model_dump(mode="json")
            execution = result_dict.get("execution") or {}
            evaluation = result_dict.get("evaluation") or {}
            bundle = result_dict.get("learning_bundle") or {}
            package = request.authority_package

            if execution.get("project_id") != package.project_id:
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_PROJECT_MISMATCH")
            if execution.get("task_id") != package.task_id:
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_TASK_MISMATCH")
            if execution.get("state_package_id") != package.state_package_id:
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_STATE_PACKAGE_MISMATCH")
            if execution.get("changed_files") not in ([], ()):
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_MUTATION_OBSERVED")
            if result_dict.get("institutional_knowledge_promoted") is not False:
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_AUTO_PROMOTION_DENIED")
            if result_dict.get("external_review_required") is not True:
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_REVIEW_BOUNDARY_MISSING")
            if evaluation.get("run_id") != execution.get("run_id"):
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_EVALUATION_RUN_MISMATCH")
            if bundle.get("run_id") != execution.get("run_id"):
                raise ValueError("FOUR_SYSTEM_L4_AGENTIC_LEARNING_RUN_MISMATCH")

            result_sha = _sha(result_dict)
            envelope = FourSystemL4ExecutionEnvelope(
                workspace_run_id=request.workspace_run_id,
                correlation_id=request.correlation_id,
                request_sha256=request_sha,
                result_sha256=result_sha,
                agentic_result=result,
                resume_token=f"agentic-l4:{request.workspace_run_id}:{result_sha[:16]}",
            )
            self.journal.save(
                AgenticL4JournalRecord(
                    workspace_run_id=request.workspace_run_id,
                    correlation_id=request.correlation_id,
                    request_sha256=request_sha,
                    status="COMPLETED",
                    result=envelope.model_dump(mode="json"),
                )
            )
            return envelope
        except Exception as error:
            self.journal.save(
                AgenticL4JournalRecord(
                    workspace_run_id=request.workspace_run_id,
                    correlation_id=request.correlation_id,
                    request_sha256=request_sha,
                    status="FAIL_CLOSED",
                    error=f"{type(error).__name__}:{error}",
                )
            )
            raise

    def resume(self, workspace_run_id: str) -> AgenticL4JournalRecord:
        record = self.journal.load(workspace_run_id)
        if record is None:
            raise ValueError("FOUR_SYSTEM_L4_AGENTIC_RUN_NOT_FOUND")
        return record


def mount_four_system_l4_agentic(
    app: FastAPI,
    *,
    project_root: Path,
    source_commit_sha: str,
    learning: AgenticLearningService,
) -> None:
    journal = AgenticL4Journal()
    service = FourSystemL4AgenticService(
        journal=journal,
        executor=lambda package: execute_integration_pilot(
            learning=learning,
            package=package,
            project_root=project_root,
            source_commit_sha=source_commit_sha,
        ),
    )
    app.state.four_system_l4_agentic_service = service

    @app.post(
        "/api/v1/agentic/integration/l4/execute",
        response_model=FourSystemL4ExecutionEnvelope,
    )
    def l4_execute(request: FourSystemL4ExecutionRequest) -> FourSystemL4ExecutionEnvelope:
        try:
            if request.authority_package.requested_provider_id != "PALWAKF_NATIVE_AGENT":
                raise AuthorityError("HERMES_OPERATIONAL_ADMISSION_CLOSED")
            return service.execute(request)
        except (AuthorityError, ValueError) as error:
            raise HTTPException(
                status_code=409,
                detail={"code": str(error), "fail_closed": True},
            ) from error

    @app.get(
        "/api/v1/agentic/integration/l4/resume/{workspace_run_id}",
        response_model=AgenticL4JournalRecord,
    )
    def l4_resume(workspace_run_id: str) -> AgenticL4JournalRecord:
        try:
            return service.resume(workspace_run_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404,
                detail={"code": str(error), "fail_closed": True},
            ) from error
