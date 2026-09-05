from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import AgentSummary, HealthResponse, TaskCreate, TaskRecord, utc_now
from .registry import list_agents
from .settings import settings
from . import store
from .command_center import mount_command_center
from .governed_operations import mount_governed_operations
from .workspace_core import mount_workspace_core
from .local_agent_core import mount_local_agent_core
from .governed_capability_foundation import mount_governed_capability_foundation
from .project_reader import mount_project_reader
from .backend_frontend_alignment import mount_backend_frontend_alignment
from .operational_core_v1 import mount_operational_core_v1
from .agentic_core_v1 import mount_agentic_core_v1
from palwakf_local_agents.open_source_capabilities_v1 import router as open_source_capabilities_v1_router
from palwakf_local_agents.open_source_tools_operational_admission_wave1_v1 import router as open_source_tools_wave1_v1_router
from palwakf_local_agents.quality_gated_read_only_operations_wave1_v1 import router as operations_wave1_v1_router
from palwakf_local_agents.quality_gated_external_scanners_wave2_v1 import router as external_scanners_wave2_v1_router
from palwakf_local_agents.full_stack_operational_waves_3_to_8_v1 import router as full_stack_waves_3_8_v1_router
from palwakf_local_agents.tool_quality_lab_wave1_v1 import router as tool_quality_lab_wave1_v1_router
from palwakf_local_agents.quality_accepted_tools_goal_planner_binding_v1 import install_quality_planner_binding
from palwakf_local_agents.first_human_authorized_read_only_operation_v1 import install_first_human_authorized_read_only_operation_v1
from palwakf_local_agents.controlled_software_development_pipeline_v1 import install_controlled_software_development_pipeline_v1
from palwakf_local_agents.governed_coding_model_provider_v1 import install_governed_coding_model_provider_v1


def _resolve_agentic_source_commit_sha(project_root: Path) -> str:
    explicit = (os.getenv("PALWAKF_AGENTIC_SOURCE_COMMIT_SHA") or "").strip()
    if explicit:
        return explicit
    try:
        process = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        candidate = process.stdout.strip()
        if process.returncode == 0 and len(candidate) == 40:
            return candidate
    except Exception:
        pass
    return "UNKNOWN_SOURCE_SHA_FAIL_CLOSED"


def create_app(project_root: Path | None = None) -> FastAPI:
    app = FastAPI(title="PalWakf Local Agent Console", version="0.1.0", docs_url="/docs", redoc_url=None)
    install_quality_planner_binding(app)
    resolved_project_root = project_root or Path(__file__).resolve().parents[3]
    install_governed_coding_model_provider_v1(app, project_root=resolved_project_root)
    install_controlled_software_development_pipeline_v1(app, project_root=resolved_project_root)
    install_first_human_authorized_read_only_operation_v1(app, project_root=resolved_project_root)
    mount_command_center(app, project_root=resolved_project_root)
    mount_governed_operations(app, project_root=resolved_project_root)
    mount_workspace_core(app, project_root=resolved_project_root)
    mount_local_agent_core(app, project_root=resolved_project_root)
    mount_governed_capability_foundation(app, project_root=resolved_project_root)
    mount_project_reader(app, project_root=resolved_project_root)
    mount_backend_frontend_alignment(app, project_root=resolved_project_root)
    mount_operational_core_v1(app, project_root=resolved_project_root)
    mount_agentic_core_v1(
        app,
        project_root=resolved_project_root,
        source_commit_sha=_resolve_agentic_source_commit_sha(resolved_project_root),
    )

    react_console_dist = resolved_project_root / "frontend" / "dist"
    react_console_index = react_console_dist / "index.html"
    react_console_assets = react_console_dist / "assets"
    if react_console_dist.is_dir() and react_console_index.is_file() and react_console_assets.is_dir():
        app.mount(
            "/agent-console/assets",
            StaticFiles(directory=react_console_assets),
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
        @app.get("/agent-console/{spa_path:path}", include_in_schema=False)
        def react_console_ui() -> FileResponse:
            return FileResponse(react_console_index, media_type="text/html; charset=utf-8")

    @app.on_event("startup")
    def startup() -> None:
        store.initialize()

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service="palwakf-local-agents",
            bind_scope="127.0.0.1_only",
            agent_execution_enabled=settings.allow_agent_execution,
            platform_mutation_enabled=settings.allow_platform_mutation,
            database_access_enabled=settings.allow_database_access,
            safety_ok=settings.safety_ok(),
            timestamp=utc_now(),
        )

    @app.get("/api/agents", response_model=list[AgentSummary])
    def agents() -> list[AgentSummary]:
        return [AgentSummary(**item) for item in list_agents()]

    @app.get("/api/tasks", response_model=list[TaskRecord])
    def tasks() -> list[TaskRecord]:
        return [TaskRecord(**item) for item in store.list_tasks()]

    @app.post("/api/tasks", response_model=TaskRecord, status_code=201)
    def create_task(_: TaskCreate) -> TaskRecord:
        raise HTTPException(
            status_code=410,
            detail={
                "code": "LEGACY_UNSCOPED_WRITE_ROUTE_DISABLED",
                "migration_target": "/api/v1/governed-capability-foundation/workspaces/{workspace_id}/tasks",
                "message_ar": "تم تعطيل مسار الكتابة القديم غير المحدد بمساحة عمل وهوية فاعل.",
            },
        )

    @app.get("/api/audit")
    def audit() -> list[dict]:
        return store.list_audit()

    @app.post("/api/tasks/{task_id}/run")
    def run_task(task_id: str) -> dict:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AGENT_EXECUTION_DISABLED",
                "task_id": task_id,
                "message_ar": "تشغيل المساعدين معطل في Foundation V1 ويحتاج بوابة قبول مستقلة.",
            },
        )

    return app


app = create_app()
app.include_router(tool_quality_lab_wave1_v1_router)
app.include_router(full_stack_waves_3_8_v1_router)
app.include_router(external_scanners_wave2_v1_router)
app.include_router(operations_wave1_v1_router)
app.include_router(open_source_tools_wave1_v1_router)
app.include_router(open_source_capabilities_v1_router)

# >>> LOCAL_AGENTS_SOURCE_NATIVE_CANDIDATE_V1_SAFE_READ_MODEL_START
from .safe_read_model_source_native_v1 import install_safe_read_model_middleware_source_native_v1 as _install_safe_read_model_middleware_source_native_v1
_install_safe_read_model_middleware_source_native_v1(app)
# <<< LOCAL_AGENTS_SOURCE_NATIVE_CANDIDATE_V1_SAFE_READ_MODEL_END
