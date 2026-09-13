from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .intersystem_v1 import WorkspaceAuthorityPackageV1
from .pre_l5_enforcement import (
    ActiveGoverningInstructionSetV1,
    ActiveInstructionV1,
    KnownFailureFingerprintV1,
    LessonReuseProofV1,
    PreL5BootstrapContextV1,
)


class PreL5InstructionProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction_id: str
    authority: str
    version: str
    effective_at: str
    applies_to_projects: tuple[str, ...]
    supersedes: tuple[str, ...] = ()


class PreL5InstructionExclusionProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction_id: str
    reason: str


class PreL5FailureFingerprintBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint_id: str
    lesson_id: str
    preventive_gate_id: str
    relevant: bool = True
    applies_to_projects: tuple[str, ...] = ("*",)


class WorkspacePreL5CrossSystemContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[
        "PALWAKF_PRE_L5_CROSS_SYSTEM_CONTRACT_V1"
    ]

    project_id: str
    task_id: str
    state_package_id: str
    execution_run_id: str
    authority_reference: str

    authority_package: WorkspaceAuthorityPackageV1

    active_instruction_set_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    active_instructions: tuple[
        PreL5InstructionProjectionV1, ...
    ]

    instruction_exclusions: tuple[
        PreL5InstructionExclusionProjectionV1, ...
    ] = ()

    active_lesson_ids: tuple[str, ...]
    reused_lesson_ids: tuple[str, ...]

    known_failure_fingerprints: tuple[
        PreL5FailureFingerprintBindingV1, ...
    ] = ()

    applicable_skill_ids: tuple[str, ...] = ()
    preventive_gate_ids: tuple[str, ...] = ()

    execution_admission: Literal["READY"]
    canonical_promotion_allowed: Literal[False]

    @model_validator(mode="after")
    def bind_workspace_contract(self):
        package = self.authority_package

        checks = (
            (
                package.project_id == self.project_id,
                "AGENTIC_WORKSPACE_PROJECT_BINDING_MISMATCH",
            ),
            (
                package.task_id == self.task_id,
                "AGENTIC_WORKSPACE_TASK_BINDING_MISMATCH",
            ),
            (
                package.state_package_id
                == self.state_package_id,
                "AGENTIC_WORKSPACE_STATE_BINDING_MISMATCH",
            ),
            (
                package.execution_run_id
                == self.execution_run_id,
                "AGENTIC_WORKSPACE_RUN_BINDING_MISMATCH",
            ),
            (
                package.authority_reference
                == self.authority_reference,
                "AGENTIC_WORKSPACE_AUTHORITY_BINDING_MISMATCH",
            ),
        )

        for passed, error in checks:
            if not passed:
                raise ValueError(error)

        active_ids = {
            item.instruction_id
            for item in self.active_instructions
        }

        excluded_ids = {
            item.instruction_id
            for item in self.instruction_exclusions
        }

        if not active_ids:
            raise ValueError(
                "AGENTIC_WORKSPACE_ACTIVE_INSTRUCTION_SET_EMPTY"
            )

        if active_ids.intersection(excluded_ids):
            raise ValueError(
                "AGENTIC_STALE_INSTRUCTION_REENTRY"
            )

        active_lessons = set(self.active_lesson_ids)
        reused_lessons = set(self.reused_lesson_ids)
        preventive = set(self.preventive_gate_ids)

        for fingerprint in self.known_failure_fingerprints:
            if not fingerprint.relevant:
                continue

            projects = set(
                fingerprint.applies_to_projects
            )

            if (
                "*" not in projects
                and self.project_id not in projects
            ):
                raise ValueError(
                    "AGENTIC_FAILURE_FINGERPRINT_PROJECT_LEAKAGE"
                )

            if fingerprint.lesson_id not in active_lessons:
                raise ValueError(
                    "AGENTIC_KNOWN_LESSON_NOT_ACTIVE"
                )

            if fingerprint.lesson_id not in reused_lessons:
                raise ValueError(
                    "AGENTIC_KNOWN_LESSON_NOT_REUSED"
                )

            if (
                fingerprint.preventive_gate_id
                not in preventive
            ):
                raise ValueError(
                    "AGENTIC_PREVENTIVE_GATE_NOT_ACTIVE"
                )

        return self


class MindReviewContextWireV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[
        "PALWAKF_PRE_L5_MIND_REVIEW_CONTEXT_V1"
    ] = "PALWAKF_PRE_L5_MIND_REVIEW_CONTEXT_V1"

    project_id: str
    task_id: str
    run_id: str
    source_sha: str = Field(
        pattern=r"^[0-9a-fA-F]{40}$"
    )

    active_instruction_set_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )

    active_lesson_ids: tuple[str, ...]
    reused_lesson_ids: tuple[str, ...]

    known_failure_fingerprints: tuple[
        PreL5FailureFingerprintBindingV1, ...
    ] = ()

    review_mode: Literal[
        "CANDIDATE_ONLY_NO_AUTO_PROMOTION"
    ] = "CANDIDATE_ONLY_NO_AUTO_PROMOTION"

    canonical_write_allowed: Literal[False] = False


def build_agentic_pre_l5_context(
    contract: WorkspacePreL5CrossSystemContractV1,
) -> PreL5BootstrapContextV1:

    historical: list[str] = []
    revoked: list[str] = []

    for item in contract.instruction_exclusions:
        if "REVOKED" in item.reason:
            revoked.append(item.instruction_id)
        else:
            historical.append(item.instruction_id)

    active = ActiveGoverningInstructionSetV1(
        project_id=contract.project_id,
        task_id=contract.task_id,
        state_package_id=contract.state_package_id,
        authorization_id=(
            f"intersystem:{contract.execution_run_id}"
        ),
        active_instructions=tuple(
            ActiveInstructionV1(
                instruction_id=item.instruction_id,
                authority=item.authority,
                version=item.version,
                effective_at=item.effective_at,
                applies_to_projects=(
                    item.applies_to_projects
                ),
                supersedes=item.supersedes,
            )
            for item in contract.active_instructions
        ),
        historical_excluded_ids=tuple(
            sorted(set(historical))
        ),
        revoked_excluded_ids=tuple(
            sorted(set(revoked))
        ),
    )

    reuse = LessonReuseProofV1(
        active_lesson_ids=contract.active_lesson_ids,
        reused_lesson_ids=contract.reused_lesson_ids,
        known_failure_fingerprints=tuple(
            KnownFailureFingerprintV1(
                fingerprint_id=item.fingerprint_id,
                lesson_id=item.lesson_id,
                preventive_gate_id=(
                    item.preventive_gate_id
                ),
                relevant=item.relevant,
                applies_to_projects=(
                    item.applies_to_projects
                ),
            )
            for item in (
                contract
                .known_failure_fingerprints
            )
        ),
    )

    return PreL5BootstrapContextV1(
        active_instruction_set=active,
        lesson_reuse=reuse,
    )


def build_mind_review_context_wire(
    *,
    contract: WorkspacePreL5CrossSystemContractV1,
    run_id: str,
) -> MindReviewContextWireV1:

    if not run_id.strip():
        raise ValueError(
            "AGENTIC_MIND_RUN_ID_REQUIRED"
        )

    return MindReviewContextWireV1(
        project_id=contract.project_id,
        task_id=contract.task_id,
        run_id=run_id,
        source_sha=(
            contract
            .authority_package
            .expected_head
        ),
        active_instruction_set_sha256=(
            contract.active_instruction_set_sha256
        ),
        active_lesson_ids=contract.active_lesson_ids,
        reused_lesson_ids=contract.reused_lesson_ids,
        known_failure_fingerprints=(
            contract.known_failure_fingerprints
        ),
    )
