from __future__ import annotations

from pydantic import ValidationError

from palwakf_local_agents.local_agent_core.contracts import AgentPreparationCreate
from palwakf_local_agents.local_agent_core.engine import prepare
from palwakf_local_agents.local_agent_core.registry import list_agents


def test_agent_preparation_accepts_governed_task_id() -> None:
    payload = AgentPreparationCreate(
        agent_id="local_agent_coordinator_v1",
        task_id="TASK-CORE-001",
        objective="Prepare a bounded local agent operating model packet.",
        requested_by="operator.local",
        requested_capabilities=["bounded_plan", "bounded_plan"],
    )
    assert payload.task_id == "TASK-CORE-001"
    assert payload.requested_capabilities == ["bounded_plan"]


def test_agent_preparation_rejects_unsafe_task_id() -> None:
    try:
        AgentPreparationCreate(
            agent_id="local_agent_coordinator_v1",
            task_id="../bad-task",
            objective="Prepare a bounded local agent operating model packet.",
            requested_by="operator.local",
        )
    except ValidationError as exc:
        assert "task_id" in str(exc)
    else:
        raise AssertionError("unsafe task_id accepted")


def test_prepare_output_is_proposal_only_and_task_bound() -> None:
    output = prepare(
        "local_agent_coordinator_v1",
        "Prepare a bounded local agent operating model packet.",
        "model_execution=NONE and pilot_execution=NOT_EXECUTED",
        [],
        {"decision": "PREPARE_ALLOWED"},
        "TASK-CORE-001",
    )
    assert output["core_agent_operating_model"] == "CORE_AGENT_OPERATING_MODEL_V1"
    assert output["task_id"] == "TASK-CORE-001"
    assert output["workspace_task_binding"] == "TASK_ID_BOUND"
    assert output["agent_output_authority"] == "PROPOSAL_ONLY_NO_EXECUTION"
    assert output["execution_state"] == "NOT_EXECUTED"
    assert output["apply_authority"] == "NONE"
    assert output["write_authority"] == "NONE"


def test_registry_declares_canonical_admission_contract() -> None:
    agents = list_agents()
    assert agents
    for agent in agents:
        assert agent["canonical_registry_contract"] == "CORE_AGENT_OPERATING_MODEL_V1"
        assert agent["canonical_admission_state"] == "admitted_prepare_only"
        assert agent["agent_output_authority"] == "PROPOSAL_ONLY_NO_EXECUTION"
        assert agent["workspace_scope"] == "REQUIRED"


if __name__ == "__main__":
    test_agent_preparation_accepts_governed_task_id()
    test_agent_preparation_rejects_unsafe_task_id()
    test_prepare_output_is_proposal_only_and_task_bound()
    test_registry_declares_canonical_admission_contract()
    print("CORE_AGENT_OPERATING_MODEL_V1_TESTS=PASS")
