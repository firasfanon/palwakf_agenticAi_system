from __future__ import annotations

import re
from collections import Counter
from typing import Any


def _terms(text: str) -> list[str]:
    return [item.lower() for item in re.findall(r"[A-Za-z؀-ۿ0-9_]{2,}", text or "")]


def _top_terms(text: str, limit: int = 8) -> list[str]:
    ignored = {"the", "and", "for", "with", "this", "that", "من", "في", "على", "إلى", "عن", "هذا", "هذه"}
    counts = Counter(term for term in _terms(text) if term not in ignored)
    return [term for term, _ in counts.most_common(limit)]


def prepare(agent_id: str, objective: str, source_summary: str, evidence_references: list[str], assessment: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:
    common = {
        "objective": objective,
        "task_id": task_id,
        "core_agent_operating_model": "CORE_AGENT_OPERATING_MODEL_V1",
        "workspace_task_binding": "TASK_ID_BOUND" if task_id else "TASK_ID_NOT_SUPPLIED_PREPARE_ONLY",
        "agent_output_authority": "PROPOSAL_ONLY_NO_EXECUTION",
        "approval_effect": "NO_EXECUTION_AUTHORITY_GRANTED",
        "apply_authority": "NONE",
        "write_authority": "NONE",
        "execution_state": "NOT_EXECUTED",
        "model_execution": "NONE",
        "pilot_execution": "NOT_EXECUTED",
        "human_review_required": True,
        "evidence_reference_count": len(evidence_references),
        "top_terms": _top_terms(f"{objective}\n{source_summary}"),
    }
    if agent_id == "policy_guardian_agent_v1":
        return {**common, "kind": "POLICY_GUARD_DECISION", "decision": assessment, "review_prompts": ["هل نطاق مساحة العمل صحيح؟", "هل طُلبت صلاحية محظورة؟", "هل المخرج تحضيري فقط؟"]}
    if agent_id == "local_agent_coordinator_v1":
        return {**common, "kind": "BOUNDED_COORDINATION_PLAN", "steps": ["Policy Guardian evaluates request", "Registered specialist prepares bounded output", "Human reviewer validates evidence", "No execution route is available"], "routing": "REGISTERED_AGENTS_ONLY"}
    if agent_id == "evidence_audit_agent_v1":
        gaps = []
        if not evidence_references:
            gaps.append("EVIDENCE_REFERENCES_MISSING")
        if "model_execution=none" not in source_summary.lower():
            gaps.append("MODEL_EXECUTION_STATE_NOT_EXPLICIT_IN_SOURCE_SUMMARY")
        return {**common, "kind": "EVIDENCE_AUDIT_PACKET", "gaps": gaps, "acceptance_state": "REVIEW_REQUIRED" if gaps else "ACCEPTANCE_CANDIDATE"}
    if agent_id == "repository_test_triage_agent_v1":
        text = source_summary.lower()
        flags = []
        if "syntaxerror" in text or "parsererror" in text: flags.append("SYNTAX_OR_PARSE")
        if "no module named" in text or "modulenotfounderror" in text: flags.append("DEPENDENCY_OR_IMPORT")
        if "assertionerror" in text or "failed" in text: flags.append("ASSERTION_OR_TEST_FAILURE")
        return {**common, "kind": "INPUT_ONLY_TRIAGE", "risk_flags": flags or ["NO_CLASSIFIED_FAILURE"], "filesystem_access": "NONE", "shell_execution": "NONE"}
    if agent_id == "task_planning_runbook_agent_v1":
        return {**common, "kind": "MEGA_BATCH_RUNBOOK_DRAFT", "phases": ["Read governing baseline", "Static verification", "Preflight and WhatIf", "Explicit Apply authorization", "Post-apply technical verification", "Runtime negative UAT", "Handoff and closure"], "rollback_prompt": "Restore only the installer-created backup after human decision."}
    if agent_id == "human_review_copilot_v1":
        return {**common, "kind": "HUMAN_REVIEW_PACKET", "review_prompts": ["Confirm agent and workspace scope.", "Confirm output remains prepare-only.", "Confirm evidence and audit references are sufficient.", "Confirm no future execution is authorized by this packet."], "approval_effect": "NO_EXECUTION_AUTHORITY_GRANTED"}
    raise KeyError("LOCAL_AGENT_NOT_FOUND")
