from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import RunRequest
from .external_contracts import ExternalContractAdapter, WorkspaceStatePackage
from .learning import EvaluationEngine, ExperienceRecord, ExperienceStore, LearningEngine
from .orchestration import MultiAgentOrchestrator
from .runtime import AgenticRuntime


class AgenticLearningService:
    def __init__(self, *, project_root: Path, source_commit_sha: str):
        self.runtime = AgenticRuntime(project_root, source_commit_sha)
        self.store = ExperienceStore()
        self.evaluator = EvaluationEngine()
        self.learner = LearningEngine()
        self.external = ExternalContractAdapter()
        self.orchestrator = MultiAgentOrchestrator()

    def execute_and_learn(self, *, package: WorkspaceStatePackage, request: RunRequest) -> dict[str, Any]:
        self.external.validate_workspace_package(package)
        self.external.validate_run_binding(package=package, request=request)
        receipt = self.runtime.execute(request)
        experience = ExperienceRecord(project_id=receipt.project_id, task_id=receipt.task_id, run_id=receipt.run_id, agent_id=receipt.agent_id, role_id=receipt.role_id, objective=request.objective, observation={"final_result": receipt.final_result, "changed_files": list(receipt.changed_files), "errors": list(receipt.errors)}, result=receipt.final_result, evidence_refs=list(receipt.evidence))
        experience_path = self.store.add_experience(experience)
        evaluation = self.evaluator.evaluate(receipt)
        evaluation_path = self.store.add_evaluation(evaluation)
        candidates = self.learner.derive(receipt=receipt, evaluation=evaluation, authorization=package.authorization)
        candidate_paths = [self.store.add_candidate(candidate) for candidate in candidates]
        mind_review = self.learner.build_mind_review(project_id=package.project_id, candidates=candidates)
        mind_submission = self.external.mind_submission(package=package, candidates=candidates)
        return {
            "receipt": receipt.model_dump(mode="json"),
            "experience": experience.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "learning_candidates": [c.model_dump(mode="json") for c in candidates],
            "mind_review": mind_review.model_dump(mode="json"),
            "mind_submission": mind_submission.model_dump(mode="json"),
            "evidence_paths": {"experience": str(experience_path), "evaluation": str(evaluation_path), "candidates": [str(p) for p in candidate_paths]},
            "institutional_knowledge_promoted": False,
            "external_review_required": True,
        }
