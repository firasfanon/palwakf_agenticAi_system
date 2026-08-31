from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

from palwakf_local_agents.local_agent_core.registry import list_agents as list_runtime_profiles
from .contracts import ProviderId, UnifiedAgent

ROLE_TO_RUNTIME = {
    "coordinator": "local_agent_coordinator_v1",
    "sovereignty_reviewer": "policy_guardian_agent_v1",
    "knowledge_researcher": "evidence_audit_agent_v1",
    "ui_ux_designer": "task_planning_runbook_agent_v1",
    "documentation_handoff": "human_review_copilot_v1",
    "product_analyst": "task_planning_runbook_agent_v1",
    "solution_architect": "task_planning_runbook_agent_v1",
    "qa_security_reviewer": "policy_guardian_agent_v1",
    "tester": "repository_test_triage_agent_v1",
    "coding_builder": "repository_test_triage_agent_v1",
    "frontend_engineer": "repository_test_triage_agent_v1",
    "backend_engineer": "repository_test_triage_agent_v1",
    "database_engineer": "policy_guardian_agent_v1",
    "release_engineer": "human_review_copilot_v1",
}

ROLE_TASK_CLASSES = {
    role: ["READ_ONLY_DIAGNOSTIC"] for role in ROLE_TO_RUNTIME
}
ROLE_TASK_CLASSES.update({
    "coordinator": ["READ_ONLY_DIAGNOSTIC", "TASK_PLANNING"],
    "sovereignty_reviewer": ["READ_ONLY_DIAGNOSTIC", "POLICY_REVIEW"],
    "knowledge_researcher": ["READ_ONLY_DIAGNOSTIC", "EVIDENCE_REVIEW"],
    "tester": ["READ_ONLY_DIAGNOSTIC", "TEST_TRIAGE"],
    "coding_builder": ["READ_ONLY_DIAGNOSTIC", "REPOSITORY_ANALYSIS"],
    "frontend_engineer": ["READ_ONLY_DIAGNOSTIC", "FRONTEND_ANALYSIS"],
    "backend_engineer": ["READ_ONLY_DIAGNOSTIC", "BACKEND_ANALYSIS"],
})


def _load_roles(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / "agents" / "registry_v2.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    roles = data.get("roles", [])
    if not isinstance(roles, list):
        raise RuntimeError("INVALID_ROLE_REGISTRY")
    return roles


def build_projection(project_root: Path, source_commit_sha: str) -> list[UnifiedAgent]:
    runtime_ids = {item["agent_id"] for item in list_runtime_profiles()}
    out: list[UnifiedAgent] = []
    for role in _load_roles(project_root):
        role_id = role["role_id"]
        runtime_id = ROLE_TO_RUNTIME.get(role_id, "UNMAPPED")
        skills = list(role.get("allowed_skills") or [])
        runnable = runtime_id in runtime_ids and bool(skills)
        out.append(UnifiedAgent(
            agent_id=f"{role_id}_agentic_v1",
            role_id=role_id,
            runtime_profile_id=runtime_id,
            skill_ids=skills,
            tool_bindings=["repository_manifest_read"],
            model_route=["ollama", "none"],
            execution_provider_policy=[ProviderId.NATIVE, ProviderId.HERMES],
            memory_scopes=["RUN_EPHEMERAL_ONLY"],
            allowed_projects=["EXTERNAL_AUTHORITY_REQUIRED"],
            permission_profile="EXTERNAL_ENVELOPE_FAIL_CLOSED",
            filesystem_scope="READ_ONLY_BY_DEFAULT",
            network_scope="DENY_BY_DEFAULT",
            data_limit="RESOURCE_BUDGET_ENFORCED",
            evidence_requirement="RUN_RECEIPT_REQUIRED",
            maturity="MEGA_BATCH_A_CANDIDATE",
            authority_status="EXTERNAL_AUTHORITY_REQUIRED",
            source_commit_sha=source_commit_sha,
            allowed_task_classes=ROLE_TASK_CLASSES.get(role_id, []),
            runnable=runnable,
        ))
    return out
