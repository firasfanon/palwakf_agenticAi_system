from __future__ import annotations

from typing import Any

from palwakf_local_agents.workspace_core.store import WorkspaceCoreStore

from .registry import get_agent

PROHIBITED_CAPABILITIES = {
    "shell", "shell_execution", "git_write", "database_write", "deployment", "external_network",
    "browser_automation", "model_execution", "pilot_execution", "cross_workspace_access", "memory_write",
}


def controls_for_workspace(workspace_core: WorkspaceCoreStore, workspace_id: str, agent_id: str) -> dict[str, Any]:
    workspace = workspace_core.workspace(workspace_id)
    policy = workspace_core.policy(workspace_id)
    agent = get_agent(agent_id)
    active = workspace["lifecycle_state"] == "active"
    return {
        "workspace_id": workspace["workspace_id"],
        "workspace_classification": workspace["classification"],
        "workspace_lifecycle_state": workspace["lifecycle_state"],
        "policy_pack_id": policy["policy_pack_id"],
        "policy_version": policy["version"],
        "agent_id": agent["agent_id"],
        "agent_execution_mode": agent["execution_mode"],
        "agent_prepare_eligible": active,
        "agent_prepare_mode": "HUMAN_EXPLICIT_LOCAL_PREPARE_ONLY" if active else "READ_ONLY_DECLARATION_ONLY_UNTIL_WORKSPACE_ACTIVATION",
        "model_adapter": "OLLAMA_COMPATIBLE_CONFIG_ONLY_DISABLED",
        "model_execution": "NONE",
        "pilot_execution": "NOT_EXECUTED",
        "external_network": "NONE",
        "shell_execution": "NONE",
        "git_write": "NONE",
        "database_write": "NONE",
        "deployment": "NONE",
        "memory_write": "NONE",
        "human_review": "MANDATORY_BEFORE_ANY_FUTURE_EXECUTION",
        "cross_workspace_access": "DENY",
        "non_transferable_constraints": policy["non_transferable_constraints"],
    }


def assess_request(controls: dict[str, Any], requested_capabilities: list[str]) -> dict[str, Any]:
    requested = sorted({item.strip().lower() for item in requested_capabilities if item.strip()})
    prohibited = sorted(set(requested) & PROHIBITED_CAPABILITIES)
    decision = "PREPARE_ALLOWED" if controls["agent_prepare_eligible"] and not prohibited else "REVIEW_OR_DENY_REQUIRED"
    return {
        "decision": decision,
        "requested_capabilities": requested,
        "prohibited_capabilities": prohibited,
        "execution_state": "NOT_EXECUTED",
        "model_execution": "NONE",
        "pilot_execution": "NOT_EXECUTED",
        "reason": "WORKSPACE_NOT_ACTIVE" if not controls["agent_prepare_eligible"] else ("PROHIBITED_CAPABILITY_REQUESTED" if prohibited else "PREPARE_ONLY_WITH_HUMAN_REVIEW"),
    }


MODEL_PILOT_WORKSPACE_ID = "palwakf_government"
MODEL_PILOT_AGENT_ID = "task_planning_runbook_agent_v1"
MODEL_PILOT_CAPABILITY = "draft_runbook"


def model_pilot_controls(controls: dict[str, Any], workspace_id: str, agent_id: str, enabled: bool) -> dict[str, Any]:
    permitted = (
        workspace_id == MODEL_PILOT_WORKSPACE_ID
        and agent_id == MODEL_PILOT_AGENT_ID
        and controls["agent_prepare_eligible"]
    )
    return {
        "pilot_scope": "ONE_WORKSPACE_ONE_AGENT_PLANNING_DRAFT_ONLY",
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "pilot_config_enabled": enabled,
        "pilot_route_enabled": permitted and enabled,
        "allowed_capabilities": [MODEL_PILOT_CAPABILITY] if permitted else [],
        "model_execution": "LOCAL_OLLAMA_PILOT" if permitted and enabled else "NONE",
        "tool_execution": "NONE",
        "shell_execution": "NONE",
        "git_write": "NONE",
        "database_write": "NONE",
        "deployment": "NONE",
        "external_network": "NONE",
        "cross_workspace_access": "DENY",
        "memory_write": "NONE",
        "human_review": "MANDATORY",
    }


def assess_model_pilot(controls: dict[str, Any], workspace_id: str, agent_id: str, enabled: bool) -> dict[str, Any]:
    pilot = model_pilot_controls(controls, workspace_id, agent_id, enabled)
    if workspace_id != MODEL_PILOT_WORKSPACE_ID:
        return {"decision": "DENY", "reason": "MODEL_PILOT_WORKSPACE_NOT_ALLOWED", "controls": pilot}
    if agent_id != MODEL_PILOT_AGENT_ID:
        return {"decision": "DENY", "reason": "MODEL_PILOT_AGENT_NOT_ALLOWED", "controls": pilot}
    if not controls["agent_prepare_eligible"]:
        return {"decision": "DENY", "reason": "WORKSPACE_NOT_ACTIVE", "controls": pilot}
    if not enabled:
        return {"decision": "DENY", "reason": "MODEL_PILOT_DISABLED", "controls": pilot}
    return {"decision": "ALLOW", "reason": "LOCAL_PLANNING_DRAFT_ONLY", "controls": pilot}
