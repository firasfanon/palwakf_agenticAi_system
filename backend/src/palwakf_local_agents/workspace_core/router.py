from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .store import WorkspaceCoreStore

STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _workspace_error(error: Exception) -> None:
    code = str(error.args[0]) if getattr(error, "args", None) else str(error)
    if code in {"WORKSPACE_NOT_FOUND", "POLICY_PACK_NOT_FOUND"}:
        raise HTTPException(status_code=404, detail={"code": code})
    if code.startswith("INVALID_") or code == "CROSS_WORKSPACE_PATH_REJECTED":
        raise HTTPException(status_code=400, detail={"code": code})
    raise error


def mount_workspace_core(app: FastAPI, project_root: Path) -> None:
    if getattr(app.state, "workspace_core_mounted", False):
        raise RuntimeError("WORKSPACE_CORE_ALREADY_MOUNTED")
    store = WorkspaceCoreStore(project_root)
    app.state.workspace_core_store = store
    app.state.workspace_core_mounted = True
    api = APIRouter(prefix="/api/v1/workspaces", tags=["workspace-core"])

    @api.get("/health")
    def health() -> dict:
        return store.health()

    @api.get("")
    def workspaces() -> dict:
        return {"items": store.list_workspaces()}

    @api.get("/{workspace_id}")
    def workspace(workspace_id: str) -> dict:
        try:
            return store.workspace(workspace_id)
        except Exception as error:  # noqa: BLE001
            _workspace_error(error)

    @api.get("/{workspace_id}/policy")
    def policy(workspace_id: str) -> dict:
        try:
            return store.policy(workspace_id)
        except Exception as error:  # noqa: BLE001
            _workspace_error(error)

    @api.get("/{workspace_id}/readiness")
    def readiness(workspace_id: str) -> dict:
        try:
            return store.readiness(workspace_id)
        except Exception as error:  # noqa: BLE001
            _workspace_error(error)

    @api.get("/{workspace_id}/audit-integrity")
    def audit_integrity(workspace_id: str) -> dict:
        try:
            return store.audit_integrity(workspace_id)
        except Exception as error:  # noqa: BLE001
            _workspace_error(error)

    app.include_router(api)
    app.mount("/workspaces/assets", StaticFiles(directory=STATIC_ROOT), name="workspace-core-assets")

    @app.get("/workspaces", include_in_schema=False)
    @app.get("/workspaces/", include_in_schema=False)
    def workspace_ui() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")
