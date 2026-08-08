from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query

from .codebase_index import CodebaseIndexer
from .contracts import (
    AttemptRegisterRequest,
    CheckpointCreateRequest,
    ContextCheckRequest,
    GoalPrepareRequest,
    InnovationReviewPrepareRequest,
    ProjectIdentityRequest,
    ProjectIdentitySimilarityRequest,
    StandingRuleUpsertRequest,
    TaskTransitionRequest,
    ToolInvokeRequest,
)
from .innovation_resilience import InnovationResilienceManager
from .model_readiness import inspect_local_model_readiness
from .state_store import GovernedLocalStateStore
from .tools import GovernedReadOnlyToolRuntime


PREFIX = "/api/v1/operational-core"


def mount_operational_core_v1(app: FastAPI, project_root: Path) -> None:
    resolved_root = project_root.resolve()
    store = GovernedLocalStateStore(resolved_root)
    indexer = CodebaseIndexer(resolved_root)
    tools = GovernedReadOnlyToolRuntime(resolved_root)
    innovation = InnovationResilienceManager(resolved_root, store)
    store.initialize()
    innovation.initialize()

    router = APIRouter(prefix=PREFIX, tags=["operational-core-v1"])

    @router.get("/health")
    def health() -> dict:
        state = store.load_state()
        return {
            "result": "PASS",
            "service": "operational-core-v1",
            "state_revision": state.get("revision", 0),
            "full_stack_vertical_slice": "available",
            "local_state_store": "json_plus_jsonl",
            "codebase_index": "read_only",
            "tool_runtime": "read_only_only",
            "standing_rules": "local_state",
            "model_readiness_gate": "probe_only_no_inference",
            "innovation_resilience_identity": "prepare_only_available",
            "execution": "blocked",
        }

    @router.get("/state")
    def get_state() -> dict:
        return store.load_state()

    @router.get("/events")
    def get_events(limit: int = Query(default=100, ge=1, le=500)) -> dict:
        events = store.list_events(limit)
        return {"events": events, "count": len(events), "storage": "append_only_jsonl"}

    @router.post("/goal/prepare")
    def prepare_goal(request: GoalPrepareRequest) -> dict:
        state = store.prepare_goal(request.model_dump())
        return {"result": "PREPARED", "state": state, "execution_authority": "none", "persistence": "local_json_jsonl"}

    @router.post("/tasks/{task_id}/transition")
    def transition_task(task_id: str, request: TaskTransitionRequest) -> dict:
        try:
            state = store.transition_task(task_id, request.action, request.note)
        except KeyError:
            raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "task_id": task_id})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": str(exc)})
        return {"result": "UPDATED", "state": state, "execution_authority": "none"}

    @router.get("/project-board")
    def project_board() -> dict:
        state = store.load_state()
        tasks = state.get("tasks", [])
        lanes = {
            "draft": [t for t in tasks if t.get("status") == "draft"],
            "ready_for_review": [t for t in tasks if t.get("status") == "ready_for_review"],
            "accepted_as_plan": [t for t in tasks if t.get("status") == "accepted_as_plan"],
            "returned": [t for t in tasks if t.get("status") == "returned"],
        }
        return {"state_revision": state.get("revision"), "goal": state.get("current_goal"), "lanes": lanes, "execution": state.get("execution")}

    @router.get("/codebase-index")
    def codebase_index(limit: int = Query(default=200, ge=20, le=500)) -> dict:
        return indexer.build(detail_limit=limit)

    @router.get("/tools")
    def list_tools() -> dict:
        registered = tools.list_tools()
        return {"tools": registered, "count": len(registered), "runtime": "governed_read_only"}

    @router.post("/tools/{tool_id}/invoke")
    def invoke_tool(tool_id: str, request: ToolInvokeRequest) -> dict:
        try:
            return tools.invoke(tool_id, path=request.path, limit=request.limit)
        except KeyError:
            raise HTTPException(status_code=404, detail={"code": "TOOL_NOT_FOUND", "tool_id": tool_id})
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail={"code": "FILE_NOT_FOUND", "path": str(exc)})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": str(exc)})

    @router.get("/standing-rules")
    def standing_rules() -> dict:
        rules = store.list_rules()
        return {"rules": rules, "count": len(rules), "persistence": "local_json"}

    @router.put("/standing-rules/{rule_id}")
    def upsert_standing_rule(rule_id: str, request: StandingRuleUpsertRequest) -> dict:
        try:
            item = store.upsert_rule(rule_id, request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": str(exc)})
        return {"result": "UPSERTED", "rule": item, "execution_effect": "none"}

    @router.get("/model-readiness")
    def model_readiness(probe: bool = Query(default=False)) -> dict:
        return inspect_local_model_readiness(probe=probe)

    @router.get("/innovation-resilience/health")
    def innovation_health() -> dict:
        return {"result": "PASS", "service": "innovation-resilience-project-identity-v1", "mode": "prepare_only", "model_inference": "none", "execution": "blocked"}

    @router.get("/innovation-resilience/dashboard")
    def innovation_dashboard() -> dict:
        return innovation.dashboard()

    @router.get("/innovation-reviews")
    def innovation_reviews(limit: int = Query(default=30, ge=1, le=100)) -> dict:
        reviews = innovation.list_reviews(limit)
        return {"reviews": reviews, "count": len(reviews), "mode": "prepare_only"}

    @router.post("/innovation-reviews/prepare")
    def prepare_innovation_review(request: InnovationReviewPrepareRequest) -> dict:
        review = innovation.prepare_review(request.model_dump())
        return {"result": "PREPARED", "review": review, "model_inference": "none", "execution_authority": "none"}

    @router.get("/resilience/state")
    def resilience_state() -> dict:
        return innovation.get_resilience_state()

    @router.post("/resilience/context-check")
    def resilience_context_check(request: ContextCheckRequest) -> dict:
        return innovation.context_check(request.model_dump())

    @router.post("/resilience/attempts/register")
    def resilience_attempt_register(request: AttemptRegisterRequest) -> dict:
        return innovation.register_attempt(request.model_dump())

    @router.post("/resilience/checkpoints")
    def resilience_checkpoint(request: CheckpointCreateRequest) -> dict:
        return {"result": "CREATED", "checkpoint": innovation.create_checkpoint(request.model_dump()), "snapshot_kind": "metadata_only"}

    @router.get("/project-identities")
    def project_identities() -> dict:
        return innovation.list_identities()

    @router.post("/project-identities/similarity-check")
    def project_identity_similarity(request: ProjectIdentitySimilarityRequest) -> dict:
        payload = request.model_dump()
        project_key = payload.pop("project_key")
        return innovation.similarity_check(project_key, payload)

    @router.put("/project-identities/{project_key}")
    def project_identity_upsert(project_key: str, request: ProjectIdentityRequest) -> dict:
        if not re_project_key(project_key):
            raise HTTPException(status_code=400, detail={"code": "INVALID_PROJECT_KEY"})
        return innovation.upsert_identity(project_key, request.model_dump())

    @router.get("/boundaries")
    def boundaries() -> dict:
        return {
            "local_state_write": "allowed_only_under_runtime_state/operational_core_v1",
            "source_code_write_at_runtime": "blocked",
            "database_write": "none",
            "model_inference": "none",
            "pilot": "not_executed",
            "shell": "blocked",
            "git": "blocked",
            "code_execution": "blocked",
            "self_apply": "blocked",
            "web_search": "blocked",
            "vector_db": "none",
            "automatic_retry": "blocked",
            "checkpoint": "metadata_only",
            "localhost_ollama_tags_probe": "optional_get_only",
        }

    app.include_router(router)


def re_project_key(value: str) -> bool:
    import re
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_.-]{1,79}", value))
