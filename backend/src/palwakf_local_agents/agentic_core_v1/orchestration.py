from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .contracts import ProviderId, RunRequest
from .external_contracts import WorkspaceStatePackage


class DelegationNode(BaseModel):
    node_id: str = Field(default_factory=lambda: f"node-{uuid4()}")
    parent_node_id: str | None = None
    agent_id: str
    role_id: str
    task_class: str
    objective: str
    provider_id: ProviderId
    skill_ids: list[str]
    status: str = "PLANNED"


class DelegationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan-{uuid4()}")
    project_id: str
    task_id: str
    nodes: list[DelegationNode]


class MultiAgentOrchestrator:
    def plan(self, *, package: WorkspaceStatePackage, primary: RunRequest, delegates: list[RunRequest]) -> DelegationPlan:
        auth = package.authorization
        requests = [primary, *delegates]
        nodes: list[DelegationNode] = []
        for index, request in enumerate(requests):
            if request.project_id != package.project_id or request.task_id != package.task_id:
                raise ValueError("DELEGATION_CROSS_PROJECT_OR_TASK_DENIED")
            if request.agent_id not in auth.allowed_agent_ids:
                raise ValueError("DELEGATION_AGENT_AUTHORITY_EXPANSION_DENIED")
            if request.task_class not in auth.allowed_task_classes:
                raise ValueError("DELEGATION_TASK_CLASS_AUTHORITY_EXPANSION_DENIED")
            if request.provider_id not in auth.allowed_provider_ids:
                raise ValueError("DELEGATION_PROVIDER_AUTHORITY_EXPANSION_DENIED")
            nodes.append(DelegationNode(parent_node_id=None if index == 0 else nodes[0].node_id, agent_id=request.agent_id, role_id=request.role_id, task_class=request.task_class, objective=request.objective, provider_id=request.provider_id, skill_ids=request.skill_ids))
        return DelegationPlan(project_id=package.project_id, task_id=package.task_id, nodes=nodes)

    def provider_policy(self, package: WorkspaceStatePackage) -> dict[str, Any]:
        return {
            "execution_providers": [p.value for p in package.authorization.allowed_provider_ids],
            "model_providers": list(package.authorization.allowed_model_providers),
            "replaceable": len(package.authorization.allowed_provider_ids) > 1 or len(package.authorization.allowed_model_providers) > 1,
            "policy_source": "EXTERNAL_AUTHORIZATION_ENVELOPE",
        }
