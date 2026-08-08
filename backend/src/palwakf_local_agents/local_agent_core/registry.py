from __future__ import annotations

from typing import Any

AGENT_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "agent_id": "policy_guardian_agent_v1",
        "display_name": "Policy Guardian",
        "arabic_name": "وكيل حارس السياسة",
        "purpose": "Evaluates a requested preparation against workspace policy and non-transferable restrictions.",
        "allowed_capabilities": ["policy_review", "risk_flags", "review_gate"],
        "execution_mode": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
        "model_execution": "NONE",
        "human_review": "REQUIRED_FOR_FUTURE_EXECUTION",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
    {
        "agent_id": "local_agent_coordinator_v1",
        "display_name": "Local Agent Coordinator",
        "arabic_name": "وكيل منسق الوكلاء المحليين",
        "purpose": "Creates a bounded preparation route and selects only registered specialist roles.",
        "allowed_capabilities": ["request_routing", "agent_selection", "bounded_plan"],
        "execution_mode": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
        "model_execution": "NONE",
        "human_review": "REQUIRED_FOR_FUTURE_EXECUTION",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
    {
        "agent_id": "evidence_audit_agent_v1",
        "display_name": "Evidence and Audit Analyst",
        "arabic_name": "وكيل تحليل الأدلة والتدقيق",
        "purpose": "Summarizes supplied evidence references and identifies acceptance gaps without changing source evidence.",
        "allowed_capabilities": ["evidence_summary", "gap_detection", "audit_packet"],
        "execution_mode": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
        "model_execution": "NONE",
        "human_review": "REQUIRED_FOR_FUTURE_EXECUTION",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
    {
        "agent_id": "repository_test_triage_agent_v1",
        "display_name": "Repository and Test Triage",
        "arabic_name": "وكيل فحص المستودع وفرز الاختبارات",
        "purpose": "Classifies supplied repository manifests and test output. It has no filesystem, shell, or git permission.",
        "allowed_capabilities": ["manifest_analysis", "test_failure_triage", "risk_flags"],
        "execution_mode": "INPUT_ONLY_ANALYSIS",
        "model_execution": "NONE",
        "human_review": "REQUIRED_FOR_FUTURE_EXECUTION",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
    {
        "agent_id": "task_planning_runbook_agent_v1",
        "display_name": "Task Planning and Runbook",
        "arabic_name": "وكيل تخطيط المهام وإجراءات التشغيل",
        "purpose": "Creates a controlled preparation plan, acceptance gates, and rollback prompts from the human-provided objective.",
        "allowed_capabilities": ["mega_batch_plan", "uat_plan", "rollback_prompts"],
        "execution_mode": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
        "model_execution": "NONE",
        "human_review": "REQUIRED_FOR_FUTURE_EXECUTION",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
    {
        "agent_id": "human_review_copilot_v1",
        "display_name": "Human Review Copilot",
        "arabic_name": "مساعد المراجعة البشرية",
        "purpose": "Packages policy decision, evidence references, and execution prohibition for a human reviewer.",
        "allowed_capabilities": ["review_packet", "decision_prompts", "evidence_links"],
        "execution_mode": "LOCAL_DETERMINISTIC_PREPARE_ONLY",
        "model_execution": "NONE",
        "human_review": "MANDATORY",
        "canonical_registry_contract": "CORE_AGENT_OPERATING_MODEL_V1",
        "canonical_admission_state": "admitted_prepare_only",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "workspace_scope": "REQUIRED",
        "task_binding": "OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION",
    },
)

_BY_ID = {item["agent_id"]: item for item in AGENT_REGISTRY}


def list_agents() -> list[dict[str, Any]]:
    return [dict(item) for item in AGENT_REGISTRY]


def get_agent(agent_id: str) -> dict[str, Any]:
    try:
        return dict(_BY_ID[agent_id])
    except KeyError as error:
        raise KeyError("LOCAL_AGENT_NOT_FOUND") from error
