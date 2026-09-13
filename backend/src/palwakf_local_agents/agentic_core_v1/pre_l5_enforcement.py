from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import ProviderId, RunReceipt, RunRequest


class ActiveInstructionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction_id: str
    authority: str
    version: str
    effective_at: str
    status: Literal["ACTIVE"] = "ACTIVE"
    applies_to_projects: tuple[str, ...] = ("*",)
    supersedes: tuple[str, ...] = ()


class ActiveGoverningInstructionSetV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolver_id: Literal["PALWAKF_ACTIVE_INSTRUCTION_RESOLVER_V1"] = (
        "PALWAKF_ACTIVE_INSTRUCTION_RESOLVER_V1"
    )
    resolution_status: Literal["RESOLVED"] = "RESOLVED"

    project_id: str
    task_id: str
    state_package_id: str
    authorization_id: str

    active_instructions: tuple[ActiveInstructionV1, ...]
    historical_excluded_ids: tuple[str, ...] = ()
    revoked_excluded_ids: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def fail_closed(self):
        if self.conflicts:
            raise ValueError("CONFLICTING_ACTIVE_INSTRUCTIONS")

        if not self.active_instructions:
            raise ValueError("ACTIVE_INSTRUCTION_SET_REQUIRED")

        ids = [
            item.instruction_id
            for item in self.active_instructions
        ]

        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_ACTIVE_INSTRUCTION")

        for instruction in self.active_instructions:
            projects = set(instruction.applies_to_projects)

            if (
                "*" not in projects
                and self.project_id not in projects
            ):
                raise ValueError(
                    "INSTRUCTION_PROJECT_APPLICABILITY_MISMATCH"
                )

        active_ids = set(ids)

        if active_ids.intersection(
            self.historical_excluded_ids
        ):
            raise ValueError(
                "HISTORICAL_INSTRUCTION_REENTERED_ACTIVE_CONTEXT"
            )

        if active_ids.intersection(
            self.revoked_excluded_ids
        ):
            raise ValueError(
                "REVOKED_INSTRUCTION_REENTERED_ACTIVE_CONTEXT"
            )

        return self


class KnownFailureFingerprintV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint_id: str
    lesson_id: str
    preventive_gate_id: str
    relevant: bool = True
    applies_to_projects: tuple[str, ...] = ("*",)


class LessonReuseProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_lesson_ids: tuple[str, ...]
    reused_lesson_ids: tuple[str, ...]
    known_failure_fingerprints: tuple[
        KnownFailureFingerprintV1, ...
    ] = ()

    @model_validator(mode="after")
    def enforce_reuse(self):
        active = set(self.active_lesson_ids)
        reused = set(self.reused_lesson_ids)

        for fingerprint in self.known_failure_fingerprints:
            if not fingerprint.relevant:
                continue

            if fingerprint.lesson_id not in active:
                raise ValueError(
                    "KNOWN_RELEVANT_LESSON_NOT_ACTIVE"
                )

            if fingerprint.lesson_id not in reused:
                raise ValueError(
                    "KNOWN_RELEVANT_LESSON_NOT_REUSED"
                )

        return self


class PreL5BootstrapContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_instruction_set: ActiveGoverningInstructionSetV1
    lesson_reuse: LessonReuseProofV1

    def instruction_set_digest(self) -> str:
        payload = self.active_instruction_set.model_dump(
            mode="json"
        )
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(encoded).hexdigest()


class ProviderModelRequirementsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_context_window: int = Field(ge=1)
    reasoning_required: bool = False
    required_endpoint_modes: tuple[str, ...]
    required_tool_capabilities: tuple[str, ...] = ()
    required_agent_capabilities: tuple[str, ...] = ()

    required_locality: Literal[
        "LOCAL_ONLY",
        "ANY",
    ] = "LOCAL_ONLY"

    required_privacy: Literal[
        "LOCAL_ONLY",
        "ALLOW_REMOTE",
    ] = "LOCAL_ONLY"


class ProviderModelCapabilityProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: ProviderId
    model_provider: str
    model_id: str | None

    context_window: int = Field(ge=1)
    reasoning_capable: bool

    endpoint_modes: tuple[str, ...]
    tool_capabilities: tuple[str, ...]
    agent_capabilities: tuple[str, ...]

    locality: Literal["LOCAL", "REMOTE"]
    privacy: Literal["LOCAL", "REMOTE"]


class FivePartExecutionEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_success: bool
    policy_success: bool
    tool_execution_success: bool
    objective_success: bool
    postcondition_success: bool

    # Observation of a tool call is recorded separately on purpose.
    tool_call_observed: bool

    @property
    def trustworthy_pass(self) -> bool:
        return all(
            (
                self.process_success,
                self.policy_success,
                self.tool_execution_success,
                self.objective_success,
                self.postcondition_success,
            )
        )


class PreL5ExecutionGuard:
    def __init__(
        self,
        *,
        context: PreL5BootstrapContextV1,
        requirements: ProviderModelRequirementsV1,
        capability_proof: ProviderModelCapabilityProofV1,
    ):
        self.context = context
        self.requirements = requirements
        self.capability_proof = capability_proof

    def _validate_capability_intersection(
        self,
        request: RunRequest,
    ) -> None:
        proof = self.capability_proof
        requirements = self.requirements

        if proof.provider_id != request.provider_id:
            raise ValueError(
                "PROVIDER_CAPABILITY_PROVIDER_MISMATCH"
            )

        if proof.model_provider != request.model_provider:
            raise ValueError(
                "PROVIDER_CAPABILITY_MODEL_PROVIDER_MISMATCH"
            )

        if proof.model_id != request.model_id:
            raise ValueError(
                "PROVIDER_CAPABILITY_MODEL_ID_MISMATCH"
            )

        if (
            proof.context_window
            < requirements.min_context_window
        ):
            raise ValueError(
                "MODEL_CONTEXT_WINDOW_INSUFFICIENT"
            )

        if (
            requirements.reasoning_required
            and not proof.reasoning_capable
        ):
            raise ValueError(
                "MODEL_REASONING_CAPABILITY_INSUFFICIENT"
            )

        if not set(
            requirements.required_endpoint_modes
        ).issubset(set(proof.endpoint_modes)):
            raise ValueError(
                "MODEL_ENDPOINT_COMPATIBILITY_MISMATCH"
            )

        if not set(
            requirements.required_tool_capabilities
        ).issubset(set(proof.tool_capabilities)):
            raise ValueError(
                "MODEL_TOOL_CAPABILITY_MISMATCH"
            )

        if not set(
            requirements.required_agent_capabilities
        ).issubset(set(proof.agent_capabilities)):
            raise ValueError(
                "MODEL_AGENT_REQUIREMENT_MISMATCH"
            )

        if not set(request.tools).issubset(
            set(proof.tool_capabilities)
        ):
            raise ValueError(
                "REQUEST_TOOL_CAPABILITY_INTERSECTION_FAIL"
            )

        if (
            requirements.required_locality == "LOCAL_ONLY"
            and proof.locality != "LOCAL"
        ):
            raise ValueError(
                "PROVIDER_LOCALITY_POLICY_MISMATCH"
            )

        if (
            requirements.required_privacy == "LOCAL_ONLY"
            and proof.privacy != "LOCAL"
        ):
            raise ValueError(
                "PROVIDER_PRIVACY_POLICY_MISMATCH"
            )

    def validate_before(
        self,
        request: RunRequest,
    ) -> None:
        active = self.context.active_instruction_set

        if active.project_id != request.project_id:
            raise ValueError(
                "ACTIVE_INSTRUCTION_PROJECT_BINDING_MISMATCH"
            )

        if active.task_id != request.task_id:
            raise ValueError(
                "ACTIVE_INSTRUCTION_TASK_BINDING_MISMATCH"
            )

        if (
            active.state_package_id
            != request.state_package_id
        ):
            raise ValueError(
                "ACTIVE_INSTRUCTION_STATE_PACKAGE_MISMATCH"
            )

        if (
            active.authorization_id
            != request.authorization.authorization_id
        ):
            raise ValueError(
                "ACTIVE_INSTRUCTION_AUTHORIZATION_MISMATCH"
            )

        for fingerprint in (
            self.context
            .lesson_reuse
            .known_failure_fingerprints
        ):
            if not fingerprint.relevant:
                continue

            projects = set(
                fingerprint.applies_to_projects
            )

            if (
                "*" not in projects
                and request.project_id not in projects
            ):
                raise ValueError(
                    "FAILURE_FINGERPRINT_PROJECT_SCOPE_MISMATCH"
                )

        self._validate_capability_intersection(
            request
        )

    def validate_after(
        self,
        receipt: RunReceipt,
    ) -> FivePartExecutionEvidenceV1:
        active = self.context.active_instruction_set

        if receipt.project_id != active.project_id:
            raise ValueError(
                "EXECUTION_EVIDENCE_PROJECT_MISMATCH"
            )

        if receipt.task_id != active.task_id:
            raise ValueError(
                "EXECUTION_EVIDENCE_TASK_MISMATCH"
            )

        if receipt.state_package_id != active.state_package_id:
            raise ValueError(
                "EXECUTION_EVIDENCE_STATE_PACKAGE_MISMATCH"
            )

        if not receipt.actions:
            raise ValueError(
                "FIVE_PART_EXECUTION_ACTION_REQUIRED"
            )

        action = receipt.actions[0]

        keys = (
            "process_success",
            "policy_success",
            "tool_execution_success",
            "objective_success",
            "postcondition_success",
            "tool_call_observed",
        )

        missing = [
            key
            for key in keys
            if key not in action
        ]

        if missing:
            raise ValueError(
                "FIVE_PART_EXECUTION_EVIDENCE_INCOMPLETE:"
                + ",".join(missing)
            )

        evidence = FivePartExecutionEvidenceV1(
            **{
                key: bool(action[key])
                for key in keys
            }
        )

        if not evidence.trustworthy_pass:
            raise ValueError(
                "FIVE_PART_EXECUTION_EVIDENCE_FAIL"
            )

        if receipt.final_result != "PASS":
            raise ValueError(
                "EXECUTION_FINAL_RESULT_NOT_PASS"
            )

        return evidence

    def validate_learning_outputs(
        self,
        *,
        candidates: list[Any],
        mind_review: Any,
    ) -> None:
        expected_project = (
            self.context
            .active_instruction_set
            .project_id
        )

        for candidate in candidates:
            if candidate.project_id != expected_project:
                raise ValueError(
                    "LEARNING_CANDIDATE_PROJECT_LEAKAGE"
                )

            if (
                candidate.promotion_status
                != "EXTERNAL_REVIEW_REQUIRED"
            ):
                raise ValueError(
                    "AUTOMATIC_CANONICAL_PROMOTION_FORBIDDEN"
                )

        if mind_review.project_id != expected_project:
            raise ValueError(
                "MIND_REVIEW_PROJECT_LEAKAGE"
            )

        if mind_review.accepted_project_knowledge:
            raise ValueError(
                "MIND_SELF_PROMOTION_FORBIDDEN"
            )

        if (
            mind_review.review_mode
            != "CANDIDATE_ONLY_NO_AUTO_PROMOTION"
        ):
            raise ValueError(
                "MIND_REVIEW_MODE_NOT_GOVERNED"
            )