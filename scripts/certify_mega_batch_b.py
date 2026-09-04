from __future__ import annotations

import json
import os
from pathlib import Path

from palwakf_local_agents.agentic_core_v1.contracts import AuthorizationEnvelope, ExecutionEnvironment, FilesystemPolicy, NetworkPolicy, ProviderId, RunRequest
from palwakf_local_agents.agentic_core_v1.external_contracts import WorkspaceStatePackage
from palwakf_local_agents.agentic_core_v1.learning_service import AgenticLearningService
from palwakf_local_agents.agentic_core_v1.orchestration import MultiAgentOrchestrator
from palwakf_local_agents.agentic_core_v1.providers import HermesProvider, OllamaProvider
from palwakf_local_agents.agentic_core_v1.registry_projection import build_projection

BASE_SHA = "1807b450f17904d17cfbe418ded7d61ee5029b56"
PROJECT_ID = "PALWAKF_LOCAL_AGENTS"
TASK_ID = "AGENTIC_LEARNING_MULTI_AGENT_AND_END_TO_END_INTEGRATION_V1"
BRANCH = "task/AGENTIC_LEARNING_MULTI_AGENT_AND_END_TO_END_INTEGRATION_V1"

def emit(name: str, passed: bool, detail=None):
    print(f"{name}={'PASS' if passed else 'FAIL_CLOSED'}")
    return {"gate": name, "passed": passed, "detail": detail}

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence_root = root / "evidence" / "mega_batch_b"
    evidence_root.mkdir(parents=True, exist_ok=True)
    os.environ["PALWAKF_AGENTIC_LEARNING_EVIDENCE_ROOT"] = str(evidence_root / "learning_runtime")
    gates = []
    agent = next(a for a in build_projection(root, BASE_SHA) if a.runnable)
    task_class = agent.allowed_task_classes[0]
    auth = AuthorizationEnvelope(authorization_id="auth-b-cert", issuer="WORKSPACE_MANAGER", project_id=PROJECT_ID, task_id=TASK_ID, allowed_agent_ids=[agent.agent_id], allowed_task_classes=[task_class], allowed_provider_ids=[ProviderId.NATIVE, ProviderId.HERMES], allowed_model_providers=["none", "ollama"], allowed_filesystem_roots=[str(root)], read_only=True, allow_network_read=True, allow_network_write=False)
    env = ExecutionEnvironment(project_id=PROJECT_ID, repository="firasfanon/palwakf_agenticAi_system", task_branch=BRANCH, base_sha=BASE_SHA, expected_head=BASE_SHA, worktree=str(root), filesystem_policy=FilesystemPolicy(mode="READ_ONLY", allowed_roots=[str(root)]), network_policy=NetworkPolicy(read=True, write=False), tool_policy=[])
    package = WorkspaceStatePackage(state_package_id="state-b-cert", project_id=PROJECT_ID, task_id=TASK_ID, repository="firasfanon/palwakf_agenticAi_system", task_branch=BRANCH, base_sha=BASE_SHA, expected_head=BASE_SHA, authorization=auth, authority_source="WORKSPACE_MANAGER")
    request = RunRequest(project_id=PROJECT_ID, task_id=TASK_ID, state_package_id=package.state_package_id, agent_id=agent.agent_id, role_id=agent.role_id, task_class=task_class, objective="Mega Batch B governed E2E diagnostic and learning proof.", provider_id=ProviderId.NATIVE, provider_mode="READ_ONLY_DIAGNOSTIC", model_provider="none", skill_ids=[], tools=[], authorization=auth, environment=env)
    result = AgenticLearningService(project_root=root, source_commit_sha=BASE_SHA).execute_and_learn(package=package, request=request)
    gates.append(emit("EXTERNAL_AUTHORITY_EXECUTION", package.authority_source == "WORKSPACE_MANAGER" and result["receipt"]["final_result"] == "PASS" and result["receipt"]["changed_files"] == []))
    gates.append(emit("GOVERNED_LEARNING", result["evaluation"]["passed"] is True and len(result["learning_candidates"]) >= 1 and result["institutional_knowledge_promoted"] is False and result["external_review_required"] is True and result["mind_submission"]["auto_promotion"] is False))
    policy = MultiAgentOrchestrator().provider_policy(package)
    gates.append(emit("REPLACEABLE_PROVIDER_CONTRACT", policy["replaceable"] is True and ProviderId.NATIVE.value in policy["execution_providers"] and ProviderId.HERMES.value in policy["execution_providers"] and "ollama" in policy["model_providers"], policy))
    ollama = OllamaProvider().health()
    gates.append(emit("OLLAMA_DISCOVERY", bool(ollama.get("healthy")), ollama))
    hermes = HermesProvider().health()
    gates.append(emit("HERMES_DISCOVERY", bool(hermes.get("discovered")), hermes))
    hermes_path = root / "evidence" / "mega_batch_a" / "HERMES_READ_ONLY_CERTIFICATION.json"
    hermes_evidence = json.loads(hermes_path.read_text(encoding="utf-8")) if hermes_path.is_file() else {}
    gates.append(emit("HERMES_READ_ONLY_CERTIFICATION_INHERITED", hermes_evidence.get("certification") == "PASS", hermes_evidence))
    gates.append(emit("NO_SELF_AUTHORIZATION_OR_AUTO_PROMOTION", result["mind_review"]["accepted_project_knowledge"] is False and result["mind_submission"]["knowledge_authority"] == "EXTERNAL_MIND_WORKSPACE_REVIEW"))
    final = all(g["passed"] for g in gates)
    print("PALWAKF_AGENTIC_AI_CAN_EXECUTE_AND_LEARN_UNDER_EXTERNAL_AUTHORITY_WITH_REPLACEABLE_PROVIDERS=" + ("TRUE" if final else "FALSE"))
    print("FINAL_RESULT=" + ("PASS" if final else "FAIL_CLOSED"))
    report = {"project_id": PROJECT_ID, "mega_batch": TASK_ID, "base_sha": BASE_SHA, "gates": gates, "e2e_result": result, "final_invariant": final, "final_result": "PASS" if final else "FAIL_CLOSED"}
    path = evidence_root / "MEGA_BATCH_B_CERTIFICATION_REPORT.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"EVIDENCE={path}")
    return 0 if final else 1

if __name__ == "__main__":
    raise SystemExit(main())
