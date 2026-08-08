from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from .models import AgentSummary, HealthResponse, TaskCreate, TaskRecord, utc_now
from .registry import list_agents
from .settings import settings
from . import store
from .command_center import mount_command_center
from .governed_operations import mount_governed_operations
from .workspace_core import mount_workspace_core
from .local_agent_core import mount_local_agent_core
from .governed_capability_foundation import mount_governed_capability_foundation

app = FastAPI(title='PalWakf Local Agent Console', version='0.1.0', docs_url='/docs', redoc_url=None)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
mount_command_center(app, project_root=PROJECT_ROOT)
mount_governed_operations(app, project_root=PROJECT_ROOT)
mount_workspace_core(app, project_root=PROJECT_ROOT)
mount_local_agent_core(app, project_root=PROJECT_ROOT)
mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)

REACT_CONSOLE_DIST = PROJECT_ROOT / "frontend" / "dist"
if REACT_CONSOLE_DIST.is_dir() and (REACT_CONSOLE_DIST / "index.html").is_file():
    app.mount(
        "/agent-console/assets",
        StaticFiles(directory=REACT_CONSOLE_DIST / "assets"),
        name="local_agents_react_console_assets",
    )

    @app.get("/agent-console", include_in_schema=False)
    @app.get("/agent-console/", include_in_schema=False)
    @app.get("/agent-console/workspaces", include_in_schema=False)
    @app.get("/agent-console/tasks", include_in_schema=False)
    @app.get("/agent-console/projects", include_in_schema=False)
    @app.get("/agent-console/evidence", include_in_schema=False)
    @app.get("/agent-console/reviews", include_in_schema=False)
    @app.get("/agent-console/tools", include_in_schema=False)
    @app.get("/agent-console/diagnostics", include_in_schema=False)
    @app.get("/agent-console/pilot-control", include_in_schema=False)
    def react_console_ui() -> FileResponse:
        return FileResponse(REACT_CONSOLE_DIST / "index.html", media_type="text/html; charset=utf-8")


@app.on_event('startup')
def startup() -> None:
    store.initialize()


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        service='palwakf-local-agents',
        bind_scope='127.0.0.1_only',
        agent_execution_enabled=settings.allow_agent_execution,
        platform_mutation_enabled=settings.allow_platform_mutation,
        database_access_enabled=settings.allow_database_access,
        safety_ok=settings.safety_ok(),
        timestamp=utc_now(),
    )


@app.get('/api/agents', response_model=list[AgentSummary])
def agents() -> list[AgentSummary]:
    return [AgentSummary(**item) for item in list_agents()]


@app.get('/api/tasks', response_model=list[TaskRecord])
def tasks() -> list[TaskRecord]:
    return [TaskRecord(**item) for item in store.list_tasks()]


@app.post('/api/tasks', response_model=TaskRecord, status_code=201)
def create_task(payload: TaskCreate) -> TaskRecord:
    if settings.allow_platform_mutation or settings.allow_database_access:
        raise HTTPException(status_code=503, detail='LOCAL_SAFETY_GUARD_FAILED')
    return store.create_task(payload)


@app.get('/api/audit')
def audit() -> list[dict]:
    return store.list_audit()


@app.post('/api/tasks/{task_id}/run')
def run_task(task_id: str) -> dict:
    raise HTTPException(
        status_code=403,
        detail={
            'code': 'AGENT_EXECUTION_DISABLED',
            'task_id': task_id,
            'message_ar': 'تشغيل المساعدين معطل في Foundation V1 ويحتاج بوابة قبول مستقلة.',
        },
    )
