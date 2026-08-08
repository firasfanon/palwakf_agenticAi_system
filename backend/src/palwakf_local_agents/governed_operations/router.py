from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from palwakf_local_agents.governed_capability_foundation.authz import ActorPrincipal, authenticated_actor
from palwakf_local_agents.legacy_write_authorization import install_legacy_write_authorization_boundary
from palwakf_local_agents.workspace_core.policy import validate_identifier

from .contracts import EvidenceCreate, GovernedTaskCreate, ReviewRequest, TransitionRequest
from .store import WorkspaceGovernedOperationsStore

STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _workspace_id(value: str) -> str:
    try:
        return validate_identifier(value, "workspace")
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"code": str(error)}) from error


def mount_governed_operations(app: FastAPI, project_root: Path) -> None:
    if getattr(app.state, "governed_operations_mounted", False):
        raise RuntimeError("GOVERNED_OPERATIONS_ALREADY_MOUNTED")
    store = WorkspaceGovernedOperationsStore(project_root)
    install_legacy_write_authorization_boundary(app, project_root)
    app.state.governed_operations_store = store
    app.state.governed_operations_mounted = True
    api = APIRouter(prefix="/api/v1/governed-operations", tags=["governed-operations"])

    def _authorize(request: Request, actor: ActorPrincipal, workspace_id: str, action: str, declared_actor_id: str) -> str:
        workspace_id = _workspace_id(workspace_id)
        app.state.legacy_write_authorizer.authorize(
            request,
            actor,
            workspace_id,
            action,
            declared_actor_id=declared_actor_id,
            commercial_persistence_supported=False,
        )
        return workspace_id

    @api.get("/health")
    def health() -> dict:
        return store.health()

    @api.get("/workspaces")
    def workspace_registry() -> dict:
        return {"items": store.list_workspace_statuses()}

    @api.get("/workspaces/{workspace_id}/controls")
    def controls(workspace_id: str) -> dict:
        return store.controls(_workspace_id(workspace_id))

    @api.get("/workspaces/{workspace_id}/dashboard")
    def dashboard(workspace_id: str) -> dict:
        return store.summary(_workspace_id(workspace_id))

    @api.get("/workspaces/{workspace_id}/tasks")
    def list_tasks(workspace_id: str, status: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=250)) -> dict:
        return {"items": store.list_tasks(_workspace_id(workspace_id), status=status, limit=limit)}

    @api.post("/workspaces/{workspace_id}/tasks", status_code=201)
    def create_task(workspace_id: str, payload: GovernedTaskCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor), idempotency_key: str = Header(default="", alias="Idempotency-Key")) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "write", payload.requested_by)
        task, replayed = store.create_task(workspace_id, payload, idempotency_key)
        return {"task": task, "idempotent_replay": replayed, "readiness": store.task_readiness(workspace_id, task["task_id"])}

    @api.get("/workspaces/{workspace_id}/tasks/{task_id}")
    def task_bundle(workspace_id: str, task_id: str) -> dict:
        return store.task_bundle(_workspace_id(workspace_id), task_id)

    @api.get("/workspaces/{workspace_id}/tasks/{task_id}/history")
    def task_history(workspace_id: str, task_id: str) -> dict:
        return {"items": store.list_history(_workspace_id(workspace_id), task_id)}

    @api.get("/workspaces/{workspace_id}/tasks/{task_id}/readiness")
    def readiness(workspace_id: str, task_id: str) -> dict:
        return store.task_readiness(_workspace_id(workspace_id), task_id)

    @api.get("/workspaces/{workspace_id}/tasks/{task_id}/integrity")
    def task_integrity(workspace_id: str, task_id: str) -> dict:
        return store.task_integrity(_workspace_id(workspace_id), task_id)

    @api.post("/workspaces/{workspace_id}/tasks/{task_id}/submit")
    def submit(workspace_id: str, task_id: str, payload: TransitionRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "write", payload.actor_id)
        return store.transition(workspace_id, task_id, "inbox", payload)

    @api.post("/workspaces/{workspace_id}/tasks/{task_id}/start-review")
    def start_review(workspace_id: str, task_id: str, payload: TransitionRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "review", payload.actor_id)
        return store.transition(workspace_id, task_id, "under_review", payload)

    @api.post("/workspaces/{workspace_id}/tasks/{task_id}/review")
    def review(workspace_id: str, task_id: str, payload: ReviewRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "review", payload.actor_id)
        return store.review(workspace_id, task_id, payload)

    @api.post("/workspaces/{workspace_id}/tasks/{task_id}/archive")
    def archive(workspace_id: str, task_id: str, payload: TransitionRequest, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "write", payload.actor_id)
        return store.transition(workspace_id, task_id, "archived", payload)

    @api.get("/workspaces/{workspace_id}/reviews")
    def reviews(workspace_id: str, task_id: str | None = Query(default=None)) -> dict:
        return {"items": store.list_reviews(_workspace_id(workspace_id), task_id)}

    @api.get("/workspaces/{workspace_id}/evidence")
    def evidence(workspace_id: str, task_id: str | None = Query(default=None)) -> dict:
        return {"items": store.list_evidence(_workspace_id(workspace_id), task_id)}

    @api.post("/workspaces/{workspace_id}/evidence", status_code=201)
    def add_evidence(workspace_id: str, payload: EvidenceCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor)) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "write", payload.actor_id)
        return {"evidence": store.add_evidence(workspace_id, payload)}

    @api.get("/workspaces/{workspace_id}/integrity")
    def integrity(workspace_id: str) -> dict:
        return store.audit_integrity(_workspace_id(workspace_id))

    @api.get("/legacy/status")
    def legacy_status() -> dict:
        return {
            "legacy_governed_operations": "AUTHORIZATION_CLOSURE_CANDIDATE_V1",
            "legacy_write_routes": "ACTOR_WORKSPACE_ACTION_AND_COMMERCIAL_CLIENT_CONTEXT_GATE_REQUIRED",
            "commercial_legacy_write": "DENY_UNTIL_CLIENT_CONTEXT_PERSISTENCE_IS_IMPLEMENTED",
            "migration": "REQUIRES_SEPARATE_HUMAN_APPROVAL",
        }

    app.include_router(api)
    app.mount("/operations/assets", StaticFiles(directory=STATIC_ROOT), name="governed-operations-assets")

    @app.get("/operations", include_in_schema=False)
    @app.get("/operations/", include_in_schema=False)
    def operations_ui() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")
