from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from palwakf_local_agents.legacy_write_authorization import install_legacy_write_authorization_boundary
from palwakf_local_agents.workspace_core.policy import validate_identifier

from .authz import ActorPrincipal, LocalActorScopeRegistry, authenticated_actor, require_workspace_scope
from .contracts import DeterministicToolRequest, PilotExecutionRequest, ProjectCreate, ReviewDecision, TaskCreate
from .store import GovernedCapabilityFoundationStore


def _workspace_id(value: str) -> str:
    try:
        return validate_identifier(value, "workspace")
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"code": str(error)}) from error


def _actor_for_workspace(actor: ActorPrincipal, workspace_id: str, action: str) -> ActorPrincipal:
    require_workspace_scope(actor, workspace_id, action)
    return actor


def mount_governed_capability_foundation(app: FastAPI, project_root: Path) -> None:
    if getattr(app.state, "governed_capability_foundation_mounted", False):
        raise RuntimeError("GOVERNED_CAPABILITY_FOUNDATION_ALREADY_MOUNTED")
    store = GovernedCapabilityFoundationStore(project_root)
    app.state.governed_capability_foundation_store = store
    app.state.governed_capability_authz_registry = LocalActorScopeRegistry(project_root)
    install_legacy_write_authorization_boundary(app, project_root)
    app.state.governed_capability_foundation_mounted = True
    api = APIRouter(prefix="/api/v1/governed-capability-foundation", tags=["governed-capability-foundation"])

    def _authorize(
        request: Request,
        actor: ActorPrincipal,
        workspace_id: str,
        action: str,
        *,
        client_id: str | None = None,
        declared_actor_id: str | None = None,
    ) -> None:
        app.state.legacy_write_authorizer.authorize(
            request,
            actor,
            workspace_id,
            action,
            client_id=client_id,
            declared_actor_id=declared_actor_id,
            commercial_persistence_supported=True,
        )

    @api.get("/health")
    def health() -> dict:
        return store.health()

    @api.get("/workspaces/{workspace_id}/status")
    def workspace_status(workspace_id: str, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _actor_for_workspace(actor, workspace_id, "read")
        return store.workspace_status(workspace_id, actor)

    @api.get("/workspaces/{workspace_id}/tasks")
    def tasks(workspace_id: str, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _actor_for_workspace(actor, workspace_id, "read")
        return {"items": store.list_tasks(workspace_id, actor)}

    @api.post("/workspaces/{workspace_id}/tasks", status_code=201)
    def create_task(workspace_id: str, payload: TaskCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _authorize(request, actor, workspace_id, "write", client_id=payload.client_id)
        return store.create_task(workspace_id, payload.title, payload.description, payload.client_id, actor)

    @api.get("/workspaces/{workspace_id}/projects")
    def projects(workspace_id: str, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _actor_for_workspace(actor, workspace_id, "read")
        return {"items": store.list_projects(workspace_id, actor)}

    @api.post("/workspaces/{workspace_id}/projects", status_code=201)
    def create_project(workspace_id: str, payload: ProjectCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _authorize(request, actor, workspace_id, "write", client_id=payload.client_id)
        return store.create_project(workspace_id, payload.name, payload.description, payload.client_id, actor)

    @api.post("/workspaces/{workspace_id}/reviews", status_code=201)
    def review(workspace_id: str, payload: ReviewDecision, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _authorize(request, actor, workspace_id, "review", client_id=payload.client_id)
        return store.review(workspace_id, payload.subject_type, payload.subject_id, payload.decision, payload.rationale, payload.client_id, actor)

    @api.post("/workspaces/{workspace_id}/tools/{tool_name}", status_code=201)
    def tool(workspace_id: str, tool_name: str, payload: DeterministicToolRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _workspace_id(workspace_id)
        _authorize(request, actor, workspace_id, "tool", client_id=payload.client_id)
        return store.tool(workspace_id, tool_name, payload.text, payload.client_id, actor)

    @api.get("/pilot/status")
    def pilot_status(actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        require_workspace_scope(actor, "research_learning", "read")
        return store.pilot_status(actor)

    @api.post("/pilot/execute")
    def execute_pilot(payload: PilotExecutionRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        _authorize(
            request,
            actor,
            _workspace_id(payload.workspace_id),
            "pilot",
            declared_actor_id=payload.human_reviewer,
        )
        return store.execute_pilot(payload.workspace_id, payload.prompt, payload.human_reviewer, payload.explicit_execution_confirmation, actor)

    app.include_router(api)
