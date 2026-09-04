from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .contracts import AuthorizationEnvelope, RunReceipt, utc_now


class ExperienceRecord(BaseModel):
    experience_id: str = Field(default_factory=lambda: f"exp-{uuid4()}")
    project_id: str
    task_id: str
    run_id: str
    agent_id: str
    role_id: str
    objective: str
    observation: dict[str, Any]
    result: str
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)


class EvaluationReceipt(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: f"eval-{uuid4()}")
    project_id: str
    task_id: str
    run_id: str
    evaluator: str
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    reasons: list[str]
    created_at: str = Field(default_factory=utc_now)


class LearningCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"learn-{uuid4()}")
    project_id: str
    task_id: str
    source_run_id: str
    candidate_type: Literal["PROJECT_LESSON", "KNOWLEDGE_DELTA", "SKILL_CANDIDATE", "PREVENTIVE_GATE_CANDIDATE"]
    statement: str
    rationale: str
    evidence_refs: list[dict[str, Any]]
    promotion_status: Literal["EXTERNAL_REVIEW_REQUIRED"] = "EXTERNAL_REVIEW_REQUIRED"
    created_at: str = Field(default_factory=utc_now)


class MindReviewEnvelope(BaseModel):
    review_id: str = Field(default_factory=lambda: f"mind-{uuid4()}")
    project_id: str
    candidate_ids: list[str]
    review_mode: Literal["CANDIDATE_ONLY_NO_AUTO_PROMOTION"] = "CANDIDATE_ONLY_NO_AUTO_PROMOTION"
    accepted_project_knowledge: bool = False
    next_action: Literal["MIND_EXTERNAL_REVIEW_REQUIRED"] = "MIND_EXTERNAL_REVIEW_REQUIRED"
    created_at: str = Field(default_factory=utc_now)


class ExperienceStore:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(os.getenv("PALWAKF_AGENTIC_LEARNING_EVIDENCE_ROOT", str(Path(tempfile.gettempdir()) / "palwakf_agentic_ai_learning")))
        self.root.mkdir(parents=True, exist_ok=True)
        self.experiences: dict[str, ExperienceRecord] = {}
        self.evaluations: dict[str, EvaluationReceipt] = {}
        self.candidates: dict[str, LearningCandidate] = {}

    def add_experience(self, item: ExperienceRecord) -> Path:
        self.experiences[item.experience_id] = item
        target = self.root / f"{item.experience_id}.json"
        target.write_text(item.model_dump_json(indent=2), encoding="utf-8")
        return target

    def add_evaluation(self, item: EvaluationReceipt) -> Path:
        self.evaluations[item.evaluation_id] = item
        target = self.root / f"{item.evaluation_id}.json"
        target.write_text(item.model_dump_json(indent=2), encoding="utf-8")
        return target

    def add_candidate(self, item: LearningCandidate) -> Path:
        self.candidates[item.candidate_id] = item
        target = self.root / f"{item.candidate_id}.json"
        target.write_text(item.model_dump_json(indent=2), encoding="utf-8")
        return target


class EvaluationEngine:
    def evaluate(self, receipt: RunReceipt) -> EvaluationReceipt:
        no_write = not receipt.changed_files
        no_errors = not receipt.errors
        passed = receipt.final_result == "PASS" and no_write and no_errors
        reasons = [
            "RUN_RESULT_PASS" if receipt.final_result == "PASS" else "RUN_RESULT_NOT_PASS",
            "NO_PROJECT_MUTATION" if no_write else "PROJECT_MUTATION_OBSERVED",
            "NO_ERRORS" if no_errors else "ERRORS_PRESENT",
        ]
        return EvaluationReceipt(project_id=receipt.project_id, task_id=receipt.task_id, run_id=receipt.run_id, evaluator="PALWAKF_EVALUATION_ENGINE_V1", score=1.0 if passed else 0.0, passed=passed, reasons=reasons)


class LearningEngine:
    def derive(self, *, receipt: RunReceipt, evaluation: EvaluationReceipt, authorization: AuthorizationEnvelope) -> list[LearningCandidate]:
        if receipt.project_id != authorization.project_id:
            raise ValueError("LEARNING_CROSS_PROJECT_DENIED")
        if receipt.task_id != authorization.task_id:
            raise ValueError("LEARNING_TASK_AUTHORITY_MISMATCH")
        if not evaluation.passed:
            return []
        return [LearningCandidate(project_id=receipt.project_id, task_id=receipt.task_id, source_run_id=receipt.run_id, candidate_type="PROJECT_LESSON", statement="A governed read-only run completed under external authority with zero project mutation and evidence-backed evaluation.", rationale="Derived from a PASS run and PASS evaluation; promotion remains external.", evidence_refs=list(receipt.evidence))]

    def build_mind_review(self, *, project_id: str, candidates: list[LearningCandidate]) -> MindReviewEnvelope:
        if any(c.project_id != project_id for c in candidates):
            raise ValueError("MIND_REVIEW_CROSS_PROJECT_DENIED")
        return MindReviewEnvelope(project_id=project_id, candidate_ids=[c.candidate_id for c in candidates])
