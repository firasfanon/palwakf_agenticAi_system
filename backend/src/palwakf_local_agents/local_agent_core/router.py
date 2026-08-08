from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from palwakf_local_agents.governed_capability_foundation.authz import ActorPrincipal, authenticated_actor
from palwakf_local_agents.legacy_write_authorization import install_legacy_write_authorization_boundary
from palwakf_local_agents.workspace_core.policy import validate_identifier

from .contracts import AgentPreparationCreate, ModelPilotDraftCreate
from .store import LocalAgentCoreStore

STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _workspace_id(value: str) -> str:
    try:
        return validate_identifier(value, "workspace")
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"code": str(error)}) from error


def mount_local_agent_core(app: FastAPI, project_root: Path) -> None:
    if getattr(app.state, "local_agent_core_mounted", False):
        raise RuntimeError("LOCAL_AGENT_CORE_ALREADY_MOUNTED")
    store = LocalAgentCoreStore(project_root)
    install_legacy_write_authorization_boundary(app, project_root)
    app.state.local_agent_core_store = store
    app.state.local_agent_core_mounted = True
    api = APIRouter(prefix="/api/v1/local-agent-core", tags=["local-agent-core"])

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

    @api.get("/agents")
    def agents() -> dict:
        return {"items": store.list_agents()}

    @api.get("/workspaces/{workspace_id}/agents")
    def workspace_agents(workspace_id: str) -> dict:
        return {"items": store.workspace_agents(_workspace_id(workspace_id))}

    @api.get("/workspaces/{workspace_id}/agents/{agent_id}/controls")
    def controls(workspace_id: str, agent_id: str) -> dict:
        return store.controls(_workspace_id(workspace_id), agent_id)

    @api.get("/workspaces/{workspace_id}/memory-boundary")
    def memory_boundary(workspace_id: str) -> dict:
        return store.memory_boundary(_workspace_id(workspace_id))

    @api.get("/workspaces/{workspace_id}/model-pilot/status")
    def model_pilot_status(workspace_id: str) -> dict:
        return store.model_pilot_status(_workspace_id(workspace_id))

    @api.post("/workspaces/{workspace_id}/model-pilot/drafts", status_code=201)
    def create_model_pilot_draft(workspace_id: str, payload: ModelPilotDraftCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor), idempotency_key: str = Header(default="", alias="Idempotency-Key")) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "pilot", payload.requested_by)
        item, replayed = store.create_model_pilot_draft(workspace_id, payload, idempotency_key)
        return {"preparation": item, "idempotent_replay": replayed, "review_packets": store.list_review_packets(workspace_id)[:1]}

    @api.get("/workspaces/{workspace_id}/preparations")
    def preparations(workspace_id: str, limit: int = Query(default=100, ge=1, le=250)) -> dict:
        return {"items": store.list_preparations(_workspace_id(workspace_id), limit=limit)}

    @api.post("/workspaces/{workspace_id}/preparations", status_code=201)
    def create_preparation(workspace_id: str, payload: AgentPreparationCreate, request: Request, actor: ActorPrincipal = Depends(authenticated_actor), idempotency_key: str = Header(default="", alias="Idempotency-Key")) -> dict:
        workspace_id = _authorize(request, actor, workspace_id, "write", payload.requested_by)
        item, replayed = store.create_preparation(workspace_id, payload, idempotency_key)
        return {"preparation": item, "idempotent_replay": replayed, "review_packets": store.list_review_packets(workspace_id)[:1]}

    @api.get("/workspaces/{workspace_id}/preparations/{preparation_id}")
    def preparation(workspace_id: str, preparation_id: str) -> dict:
        return store.get_preparation(_workspace_id(workspace_id), preparation_id)

    @api.get("/workspaces/{workspace_id}/review-packets")
    def review_packets(workspace_id: str) -> dict:
        return {"items": store.list_review_packets(_workspace_id(workspace_id))}

    @api.get("/workspaces/{workspace_id}/integrity")
    def integrity(workspace_id: str) -> dict:
        return store.audit_integrity(_workspace_id(workspace_id))

    app.include_router(api)
    app.mount("/local-agents/assets", StaticFiles(directory=STATIC_ROOT), name="local-agent-core-assets")

    @app.get("/local-agents", include_in_schema=False)
    @app.get("/local-agents/", include_in_schema=False)
    def local_agents_ui() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")
