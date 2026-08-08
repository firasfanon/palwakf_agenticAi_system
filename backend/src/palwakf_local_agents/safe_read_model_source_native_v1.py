"""Browser-safe read projections for Local Agents operational GET responses (Source-Native Candidate V1).

This is a response-only allowlist boundary. It does not write storage, start agents,
invoke models, start pilots, change routing, read project files, or authorize actions.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_TARGET_PATHS = {
    "/health",
    "/api/v1/local-agents/dashboard",
    "/api/v1/local-agents/tasks",
    "/api/v1/local-agents/reviews",
    "/api/v1/local-agents/evidence",
    "/api/v1/local-agent-core/agents",
    "/api/v1/workspaces",
    "/api/v1/governed-operations/workspaces",
    "/api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/status",
}

_SYSTEM_POSTURE_FIELDS = (
    "MODEL_EXECUTION", "PILOT_EXECUTION", "TOOL_EXECUTION", "EXTERNAL_NETWORK",
    "PLATFORM_MUTATION", "DATABASE_ACCESS", "BIND_SCOPE",
)
_WORKSPACE_FIELDS = (
    "workspace_id", "display_name", "classification", "policy_pack_id",
    "policy_version", "lifecycle_state", "execution_mode", "isolation_contract",
)
_GOVERNED_FIELDS = (
    "workspace_id", "display_name", "classification", "lifecycle_state",
    "policy_pack_id", "policy_version",
)
_PERMISSION_FIELDS = (
    "workspace_id", "policy_pack_id", "policy_version", "workspace_lifecycle_state",
    "operation_scope", "agent_profile", "requested_roles", "permitted_roles",
    "execution_gateway", "model_execution", "pilot_execution", "tool_execution",
    "external_network", "platform_mutation", "cross_workspace_read",
    "cross_workspace_write", "memory_write", "approval_is_execution", "human_review",
)
_TASK_FIELDS = (
    "queue", "task_id", "title", "status", "risk", "autonomy",
    "requested_agent", "human_approval_required", "created_at", "updated_at",
)
_REVIEW_FIELDS = (
    "review_id", "record_type", "task_id", "decision", "scope",
    "transition_status", "created_at",
)
_EVIDENCE_FIELDS = ("category", "id", "task_id", "status", "created_at")
_AGENT_FIELDS = (
    "agent_id", "display_name", "purpose", "execution_mode", "model_execution",
    "human_review", "status",
)
_PILOT_FIELDS = (
    "status", "model_execution", "pilot_execution", "execution_gateway",
    "workspace_id", "human_review", "reason", "message",
)
_HEALTH_FIELDS = (
    "service", "bind_scope", "agent_execution_enabled", "platform_mutation_enabled",
    "database_access_enabled", "safety_ok",
)


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _pick(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    source = _record(value)
    return {field: source[field] for field in fields if field in source}


def _items(value: Any) -> list[dict[str, Any]]:
    raw = _record(value).get("items")
    return [dict(item) for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _metadata(value: Any) -> dict[str, Any]:
    return _record(_record(value).get("metadata"))


def _is_canonical_operational_evidence(value: Any) -> bool:
    # Evidence is shown only when the publisher marks it explicitly. No path heuristic.
    return _metadata(value).get("canonical_operational_evidence") is True


def _project_dashboard(payload: Any) -> dict[str, Any]:
    source = _record(payload)
    raw_evidence = _mapping_list(source.get("latest_evidence"))
    canonical = [item for item in raw_evidence if _is_canonical_operational_evidence(item)]
    counts = _record(source.get("counts"))
    safe_counts = {name: counts[name] for name in ("inbox", "approved", "archived", "reviews") if name in counts}
    safe_counts["evidence"] = len(canonical) if canonical else None
    return {
        "system_posture": _pick(source.get("system_posture"), _SYSTEM_POSTURE_FIELDS),
        "counts": safe_counts,
        "active_approved_tasks": [_pick(item, _TASK_FIELDS) for item in _mapping_list(source.get("active_approved_tasks"))],
        "latest_reviews": [_pick(item, _REVIEW_FIELDS) for item in _mapping_list(source.get("latest_reviews"))],
        "latest_evidence": [_pick(item, _EVIDENCE_FIELDS) for item in canonical],
        "evidence_disclosure": {
            "canonical_records_available": bool(canonical),
            "historical_or_generated_artifacts_excluded": max(len(raw_evidence) - len(canonical), 0),
            "canonical_count_not_published": not bool(canonical),
        },
    }


def _project_collection(payload: Any, fields: tuple[str, ...], *, canonical_only: bool = False) -> dict[str, Any]:
    rows = _items(payload)
    if canonical_only:
        rows = [row for row in rows if _is_canonical_operational_evidence(row)]
    return {"items": [_pick(row, fields) for row in rows]}


def _project_governed_workspaces(payload: Any) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in _items(payload):
        safe = _pick(item, _GOVERNED_FIELDS)
        safe["permission_intersection"] = _pick(_record(item).get("permission_intersection"), _PERMISSION_FIELDS)
        rows.append(safe)
    return {"items": rows}


def project_read_model(path: str, payload: Any) -> Any:
    """Project only known local GET payloads; all other payloads pass through unchanged."""
    if path == "/health":
        return _pick(payload, _HEALTH_FIELDS)
    if path == "/api/v1/local-agents/dashboard":
        return _project_dashboard(payload)
    if path == "/api/v1/local-agents/tasks":
        return _project_collection(payload, _TASK_FIELDS)
    if path == "/api/v1/local-agents/reviews":
        return _project_collection(payload, _REVIEW_FIELDS)
    if path == "/api/v1/local-agents/evidence":
        return _project_collection(payload, _EVIDENCE_FIELDS, canonical_only=True)
    if path == "/api/v1/local-agent-core/agents":
        return _project_collection(payload, _AGENT_FIELDS)
    if path == "/api/v1/workspaces":
        return _project_collection(payload, _WORKSPACE_FIELDS)
    if path == "/api/v1/governed-operations/workspaces":
        return _project_governed_workspaces(payload)
    if path == "/api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/status":
        return _pick(payload, _PILOT_FIELDS)
    return payload


class SafeReadModelMiddlewareSourceNativeV1(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        if request.method != "GET" or request.url.path not in _TARGET_PATHS:
            return response
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or "application/json" not in content_type.lower():
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)
        headers = {key: value for key, value in response.headers.items() if key.lower() not in {"content-length", "content-type"}}
        return JSONResponse(content=project_read_model(request.url.path, payload), status_code=response.status_code, headers=headers)


def install_safe_read_model_middleware_source_native_v1(app: Any) -> None:
    """Install once on the existing FastAPI app without changing routes or application state."""
    state_key = "local_agents_safe_read_model_middleware_source_native_v1_installed"
    if getattr(app.state, state_key, False):
        return
    app.add_middleware(SafeReadModelMiddlewareSourceNativeV1)
    setattr(app.state, state_key, True)
