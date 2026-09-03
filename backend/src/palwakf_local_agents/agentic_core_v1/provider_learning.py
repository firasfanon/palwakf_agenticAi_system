from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from .learning import EvaluationReceipt, ExperienceRecord, LearningCandidate
from .providers import HermesProvider, OllamaProvider


def _provider_candidate_statement(provider_id: str, observation: dict[str, Any]) -> str:
    healthy = bool(observation.get("healthy"))
    if provider_id == "ollama":
        models = observation.get("models") or []
        latency = observation.get("latency_ms")
        return (
            f"Ollama provider diagnostic observed healthy={healthy}, "
            f"model_count={len(models)}, latency_ms={latency}."
        )
    discovered = bool(observation.get("discovered"))
    certification = observation.get("certification", "UNKNOWN")
    return (
        f"Hermes provider diagnostic observed discovered={discovered}, "
        f"healthy={healthy}, certification={certification}."
    )


def collect_provider_learning(
    *,
    learning,
    package,
    execution_receipt: dict[str, Any],
) -> dict[str, Any]:
    capabilities = set(package.required_capabilities)
    observations: list[dict[str, Any]] = []
    experiences: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    candidates: list[LearningCandidate] = []

    probes: list[tuple[str, str, Any]] = []
    if "OLLAMA_PROVIDER_LEARNING" in capabilities:
        if not package.allow_network_read:
            raise ValueError("OLLAMA_PROVIDER_NETWORK_READ_NOT_AUTHORIZED")
        ollama = OllamaProvider()
        host = urlparse(ollama.endpoint).hostname
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("OLLAMA_PROVIDER_ENDPOINT_NOT_LOCAL")
        probes.append(("MODEL_PROVIDER", "ollama", ollama))
    if "HERMES_PROVIDER_LEARNING" in capabilities:
        probes.append(("EXECUTION_PROVIDER", "HERMES_AGENT", HermesProvider()))

    for provider_kind, provider_id, provider in probes:
        try:
            observation = provider.health()
            probe_completed = True
        except Exception as error:
            observation = {
                "provider_id": provider_id,
                "healthy": False,
                "error": f"{type(error).__name__}: {error}",
            }
            probe_completed = True

        record = {
            "provider_kind": provider_kind,
            "provider_id": provider_id,
            "probe": "HEALTH_AND_CAPABILITY_DIAGNOSTIC",
            "probe_completed": probe_completed,
            "observation": observation,
        }
        observations.append(record)

        healthy = bool(observation.get("healthy"))
        experience = ExperienceRecord(
            project_id=package.project_id,
            task_id=package.task_id,
            run_id=execution_receipt["run_id"],
            agent_id=execution_receipt["agent_id"],
            role_id=execution_receipt["role_id"],
            objective=f"Observe provider {provider_id} under governed read-only authority.",
            observation=record,
            result="PASS" if healthy else "FAIL",
            evidence_refs=[],
        )
        experience_path = learning.store.add_experience(experience)

        evaluation = EvaluationReceipt(
            project_id=package.project_id,
            task_id=package.task_id,
            run_id=execution_receipt["run_id"],
            evaluator="PALWAKF_PROVIDER_EVALUATION_ENGINE_V1",
            score=1.0 if healthy else 0.0,
            passed=healthy,
            reasons=[
                "PROVIDER_PROBE_COMPLETED",
                "PROVIDER_HEALTHY" if healthy else "PROVIDER_UNHEALTHY",
                f"PROVIDER_ID={provider_id}",
            ],
        )
        evaluation_path = learning.store.add_evaluation(evaluation)

        candidate = LearningCandidate(
            project_id=package.project_id,
            task_id=package.task_id,
            source_run_id=execution_receipt["run_id"],
            candidate_type="PROJECT_LESSON",
            statement=_provider_candidate_statement(provider_id, observation),
            rationale=(
                "Derived from a governed provider diagnostic. "
                "The observation is evidence, not automatic institutional knowledge."
            ),
            evidence_refs=[
                {
                    "type": "PROVIDER_EXPERIENCE_JSON",
                    "path": str(experience_path),
                    "provider_id": provider_id,
                },
                {
                    "type": "PROVIDER_EVALUATION_JSON",
                    "path": str(evaluation_path),
                    "provider_id": provider_id,
                },
            ],
        )
        learning.store.add_candidate(candidate)

        experiences.append(experience.model_dump(mode="json"))
        evaluations.append(evaluation.model_dump(mode="json"))
        candidates.append(candidate)

    return {
        "observations": observations,
        "experiences": experiences,
        "evaluations": evaluations,
        "candidates": candidates,
    }
