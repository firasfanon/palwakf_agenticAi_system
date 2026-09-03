from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import (
    AuthorizationEnvelope,
    ExecutionEnvironment,
    FilesystemPolicy,
    NetworkPolicy,
    ProviderId,
    RunRequest,
)
from .external_contracts import WorkspaceStatePackage
from .learning_service import AgenticLearningService
from .provider_learning import collect_provider_learning
from .registry_projection import build_projection


class WorkspaceAuthorityPackageV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["PALWAKF_INTERSYSTEM_CONTRACT_V1"] = (
        "PALWAKF_INTERSYSTEM_CONTRACT_V1"
    )
    state_package_id: str
    execution_run_id: str
    project_id: str
    task_id: str
    repository: str
    task_branch: str
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    expected_head: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    authority_reference: str
    objective: str
    constraints: list[str]
    timeout_seconds: int
    scope_patterns: list[str]
    read_only: Literal[True] = True
    allow_network_read: bool = False
    allow_network_write: Literal[False] = False
    required_capabilities: list[str]
    required_tests: list[str]
    requested_provider_id: Literal["PALWAKF_NATIVE_AGENT", "HERMES_AGENT"] = (
        "PALWAKF_NATIVE_AGENT"
    )
    requested_model_provider: Literal["none", "ollama"] = "none"


class LearningCandidateItemV1(BaseModel):
    candidate_id: str
    project_id: str
    task_id: str
    candidate_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    source_sha: str


class LearningCandidateBundleV1(BaseModel):
    contract_version: Literal["PALWAKF_INTERSYSTEM_CONTRACT_V1"] = (
        "PALWAKF_INTERSYSTEM_CONTRACT_V1"
    )
    project_id: str
    task_id: str
    run_id: str
    source_sha: str
    auto_promotion: Literal[False] = False
    candidates: tuple[LearningCandidateItemV1, ...]


class AgenticIntegrationPilotResultV1(BaseModel):
    contract_version: Literal["PALWAKF_INTERSYSTEM_CONTRACT_V1"] = (
        "PALWAKF_INTERSYSTEM_CONTRACT_V1"
    )
    execution: dict
    experience: dict
    evaluation: dict
    learning_bundle: LearningCandidateBundleV1
    provider_observations: tuple[dict, ...] = ()
    provider_experiences: tuple[dict, ...] = ()
    provider_evaluations: tuple[dict, ...] = ()
    provider_learning_candidate_count: int = 0
    institutional_knowledge_promoted: Literal[False] = False
    external_review_required: Literal[True] = True


def _evidence_strings(items: list[dict]) -> tuple[str, ...]:
    refs: list[str] = []
    for item in items:
        ref = item.get("path") or item.get("reference")
        refs.append(str(ref) if ref else json.dumps(item, sort_keys=True))
    return tuple(refs)


def execute_integration_pilot(
    *,
    learning: AgenticLearningService,
    package: WorkspaceAuthorityPackageV1,
    project_root: Path,
    source_commit_sha: str,
) -> AgenticIntegrationPilotResultV1:
    if not package.task_branch.startswith("task/"):
        raise ValueError("INTERSYSTEM_TASK_BRANCH_REQUIRED")
    if package.allow_network_write:
        raise ValueError("INTERSYSTEM_NETWORK_WRITE_FORBIDDEN")
    if package.expected_head.lower() != source_commit_sha.lower():
        raise ValueError("INTERSYSTEM_EXPECTED_HEAD_SOURCE_MISMATCH")

    agents = sorted(
        (agent for agent in build_projection(project_root, source_commit_sha) if agent.runnable),
        key=lambda agent: agent.agent_id,
    )
    if not agents:
        raise ValueError("INTERSYSTEM_NO_RUNNABLE_AGENT")
    agent = agents[0]
    if not agent.allowed_task_classes:
        raise ValueError("INTERSYSTEM_AGENT_TASK_CLASS_UNAVAILABLE")
    task_class = agent.allowed_task_classes[0]

    provider = ProviderId(package.requested_provider_id)
    authorization = AuthorizationEnvelope(
        authorization_id=f"intersystem:{package.execution_run_id}",
        issuer="WORKSPACE_MANAGER",
        project_id=package.project_id,
        task_id=package.task_id,
        allowed_agent_ids=[agent.agent_id],
        allowed_task_classes=[task_class],
        allowed_provider_ids=[provider],
        allowed_model_providers=[package.requested_model_provider],
        allowed_filesystem_roots=[str(project_root)],
        allowed_path_patterns=list(package.scope_patterns),
        read_only=True,
        allow_network_read=package.allow_network_read,
        allow_network_write=False,
    )
    environment = ExecutionEnvironment(
        project_id=package.project_id,
        repository=package.repository,
        task_branch=package.task_branch,
        base_sha=package.base_sha,
        expected_head=package.expected_head,
        worktree=str(project_root),
        filesystem_policy=FilesystemPolicy(
            mode="READ_ONLY",
            allowed_roots=[str(project_root)],
            allowed_patterns=list(package.scope_patterns),
        ),
        network_policy=NetworkPolicy(
            read=package.allow_network_read,
            write=False,
        ),
        tool_policy=[],
    )
    state = WorkspaceStatePackage(
        state_package_id=package.state_package_id,
        project_id=package.project_id,
        task_id=package.task_id,
        repository=package.repository,
        task_branch=package.task_branch,
        base_sha=package.base_sha,
        expected_head=package.expected_head,
        authorization=authorization,
        authority_source="WORKSPACE_MANAGER",
    )
    request = RunRequest(
        project_id=package.project_id,
        task_id=package.task_id,
        state_package_id=package.state_package_id,
        agent_id=agent.agent_id,
        role_id=agent.role_id,
        task_class=task_class,
        objective=package.objective,
        provider_id=provider,
        provider_mode="READ_ONLY_DIAGNOSTIC",
        model_provider=package.requested_model_provider,
        skill_ids=[],
        tools=[],
        authorization=authorization,
        environment=environment,
    )

    result = learning.execute_and_learn(package=state, request=request)
    receipt = result["receipt"]
    provider_learning = collect_provider_learning(
        learning=learning,
        package=package,
        execution_receipt=receipt,
    )
    combined_learning_candidates = [
        *result["learning_candidates"],
        *[
            item.model_dump(mode="json")
            for item in provider_learning["candidates"]
        ],
    ]
    candidates = tuple(
        LearningCandidateItemV1(
            candidate_id=item["candidate_id"],
            project_id=item["project_id"],
            task_id=item["task_id"],
            candidate_type=item["candidate_type"],
            summary=item["statement"],
            evidence_refs=_evidence_strings(item.get("evidence_refs", [])),
            source_sha=package.expected_head,
        )
        for item in combined_learning_candidates
    )
    bundle = LearningCandidateBundleV1(
        project_id=package.project_id,
        task_id=package.task_id,
        run_id=receipt["run_id"],
        source_sha=package.expected_head,
        candidates=candidates,
    )
    return AgenticIntegrationPilotResultV1(
        execution=receipt,
        experience=result["experience"],
        evaluation=result["evaluation"],
        learning_bundle=bundle,
        provider_observations=tuple(provider_learning["observations"]),
        provider_experiences=tuple(provider_learning["experiences"]),
        provider_evaluations=tuple(provider_learning["evaluations"]),
        provider_learning_candidate_count=len(provider_learning["candidates"]),
    )
