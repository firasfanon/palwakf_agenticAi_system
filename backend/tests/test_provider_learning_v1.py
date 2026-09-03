from types import SimpleNamespace

import pytest

from palwakf_local_agents.agentic_core_v1.learning_service import AgenticLearningService
from palwakf_local_agents.agentic_core_v1.provider_learning import collect_provider_learning


class _FakeOllama:
    def health(self):
        return {
            "provider_id": "ollama",
            "healthy": True,
            "models": ["model-a"],
            "latency_ms": 12.5,
        }


class _FakeHermes:
    def health(self):
        return {
            "provider_id": "HERMES_AGENT",
            "discovered": True,
            "healthy": True,
            "certification": "DISCOVERED_NOT_YET_READ_ONLY_CERTIFIED",
        }


def _package(*, network_read: bool):
    return SimpleNamespace(
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="FOUR_SYSTEM_READ_ONLY_INTEGRATION_PILOT_V1",
        required_capabilities=[
            "OLLAMA_PROVIDER_LEARNING",
            "HERMES_PROVIDER_LEARNING",
        ],
        allow_network_read=network_read,
    )


def _receipt():
    return {
        "run_id": "run-provider-learning-test",
        "agent_id": "agent-test",
        "role_id": "role-test",
    }


def test_provider_learning_requires_network_read_for_ollama(tmp_path, monkeypatch):
    service = AgenticLearningService(
        project_root=tmp_path,
        source_commit_sha="1" * 40,
    )
    with pytest.raises(ValueError, match="OLLAMA_PROVIDER_NETWORK_READ_NOT_AUTHORIZED"):
        collect_provider_learning(
            learning=service,
            package=_package(network_read=False),
            execution_receipt=_receipt(),
        )


def test_provider_learning_creates_experience_evaluation_and_candidates(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.provider_learning.OllamaProvider",
        lambda: _FakeOllama(),
    )
    monkeypatch.setattr(
        "palwakf_local_agents.agentic_core_v1.provider_learning.HermesProvider",
        lambda: _FakeHermes(),
    )
    service = AgenticLearningService(
        project_root=tmp_path,
        source_commit_sha="1" * 40,
    )
    result = collect_provider_learning(
        learning=service,
        package=_package(network_read=True),
        execution_receipt=_receipt(),
    )
    assert len(result["observations"]) == 2
    assert len(result["experiences"]) == 2
    assert len(result["evaluations"]) == 2
    assert len(result["candidates"]) == 2
    assert {x["provider_id"] for x in result["observations"]} == {
        "ollama",
        "HERMES_AGENT",
    }
    assert all(c.promotion_status == "EXTERNAL_REVIEW_REQUIRED" for c in result["candidates"])
