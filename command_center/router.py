from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .read_only_store import LocalAgentsReadOnlyStore, ReadOnlyStoreError


MODULE_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = MODULE_ROOT / "static"


def _problem(exc: ReadOnlyStoreError) -> HTTPException:
    return HTTPException(status_code=404 if str(exc) in {"INVALID_TASK_ID", "TASK_NOT_FOUND_OR_AMBIGUOUS"} else 400, detail=str(exc))


def _ui_response() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html", media_type="text/html; charset=utf-8")


def mount_command_center(
    app: FastAPI,
    *,
    project_root: str | Path,
    ui_prefix: str = "/command-center",
    api_prefix: str = "/api/v1/local-agents",
) -> None:
    """Mount read-only Command Center V1 into an existing FastAPI application.

    This only registers GET routes and static assets. It has no task execution or write routes.
    """
    store = LocalAgentsReadOnlyStore(project_root)
    ui_prefix = ui_prefix.rstrip("/") or "/command-center"
    api_prefix = api_prefix.rstrip("/")

    api = APIRouter(prefix=api_prefix, tags=["Local Agents Command Center — Read Only"])

    @api.get("/dashboard")
    def dashboard() -> dict:
        return store.dashboard()

    @api.get("/tasks")
    def tasks(queue: str | None = None) -> dict:
        if queue not in {None, "inbox", "approved", "archived"}:
            raise HTTPException(status_code=400, detail="INVALID_QUEUE")
        return {"items": store.list_tasks(queue), "queue": queue or "all"}

    @api.get("/tasks/{task_id}")
    def task_detail(task_id: str) -> dict:
        try:
            return store.get_task(task_id)
        except ReadOnlyStoreError as exc:
            raise _problem(exc) from exc

    @api.get("/reviews")
    def reviews() -> dict:
        return {"items": store.list_reviews()}

    @api.get("/evidence")
    def evidence() -> dict:
        return {"items": store.list_evidence()}

    @api.get("/agents")
    def agents() -> dict:
        return {"items": store.agent_registry()}

    @api.get("/governance")
    def governance() -> dict:
        return store.governance()

    @api.get("/system-health")
    def system_health() -> dict:
        return store.system_health()

    app.include_router(api)
    app.mount(f"{ui_prefix}/assets", StaticFiles(directory=STATIC_ROOT), name="local_agents_command_center_assets")

    @app.get(ui_prefix, include_in_schema=False)
    @app.get(f"{ui_prefix}/", include_in_schema=False)
    @app.get(f"{ui_prefix}/tasks", include_in_schema=False)
    @app.get(f"{ui_prefix}/tasks/{{task_id}}", include_in_schema=False)
    @app.get(f"{ui_prefix}/reviews", include_in_schema=False)
    @app.get(f"{ui_prefix}/evidence", include_in_schema=False)
    @app.get(f"{ui_prefix}/agents", include_in_schema=False)
    @app.get(f"{ui_prefix}/governance", include_in_schema=False)
    @app.get(f"{ui_prefix}/system-health", include_in_schema=False)
    async def command_center_shell(request: Request):
        return _ui_response()
