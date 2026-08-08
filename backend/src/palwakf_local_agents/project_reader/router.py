from __future__ import annotations

from pathlib import Path
from typing import Iterable
import hashlib
import json
import re

from fastapi import APIRouter, FastAPI, HTTPException, Query

try:
    from palwakf_local_agents.workspace_core.policy import validate_identifier
except Exception:  # pragma: no cover - defensive import fallback
    def validate_identifier(value: str, _: str) -> str:
        if not value or not re.fullmatch(r"[A-Za-z0-9_.:-]{3,120}", value):
            raise ValueError("INVALID_IDENTIFIER")
        return value

BLOCKED_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", "dist", "build", ".venv", "venv"}
ALLOWED_ROOTS = ("frontend", "backend", "agents", "docs")
KEY_FILES = (
    "frontend/package.json",
    "frontend/src/App.tsx",
    "frontend/src/styles.css",
    "frontend/src/components/Layout.tsx",
    "backend/src/palwakf_local_agents/app.py",
    "backend/src/palwakf_local_agents/local_agent_core/router.py",
    "backend/src/palwakf_local_agents/command_center/router.py",
    "backend/src/palwakf_local_agents/workspace_core/router.py",
    "backend/src/palwakf_local_agents/governed_operations/router.py",
    "backend/src/palwakf_local_agents/project_reader/router.py",
    "agents/registry.yaml",
    "agents/registry_v2.yaml",
)
MAX_ROUTE_LINES_PER_FILE = 80


def _safe_workspace_id(workspace_id: str) -> str:
    try:
        return validate_identifier(workspace_id, "workspace")
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"code": str(error)}) from error


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _is_visible(path: Path) -> bool:
    return not any(part in BLOCKED_DIRS for part in path.parts)


def _iter_files(root: Path, rel_root: str) -> Iterable[Path]:
    base = root / rel_root
    if not base.exists():
        return []
    output: list[Path] = []
    for path in base.rglob("*"):
        rel = path.relative_to(root)
        if path.is_file() and _is_visible(rel):
            output.append(path)
    return output


def _count_project_files(project_root: Path) -> dict:
    roots = []
    total_files = 0
    total_bytes = 0
    for rel_root in ALLOWED_ROOTS:
        base = project_root / rel_root
        files = list(_iter_files(project_root, rel_root)) if base.exists() else []
        size = sum(path.stat().st_size for path in files if path.exists())
        roots.append({"root": rel_root, "exists": base.exists(), "file_count": len(files), "size_bytes": size})
        total_files += len(files)
        total_bytes += size
    return {"roots": roots, "total_files": total_files, "total_size_bytes": total_bytes}


def _key_file_records(project_root: Path) -> list[dict]:
    records = []
    for rel in KEY_FILES:
        path = project_root / rel
        exists = path.is_file()
        record = {"path": rel, "exists": exists}
        if exists:
            stat = path.stat()
            record.update({"size_bytes": stat.st_size, "sha256": _sha256(path)})
        records.append(record)
    return records


def _extract_route_lines(path: Path, project_root: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict] = []
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        route_like = False
        if path.suffix == ".py" and (stripped.startswith("@api.get") or stripped.startswith("@app.get") or stripped.startswith("@router.get") or "app.mount(" in stripped or "include_router" in stripped):
            route_like = True
        if path.name == "App.tsx" and ("path ===" in stripped or "agent-console" in stripped and "return <" in stripped):
            route_like = True
        if route_like:
            rows.append({"file": path.relative_to(project_root).as_posix(), "line": index, "text": stripped[:240]})
        if len(rows) >= MAX_ROUTE_LINES_PER_FILE:
            break
    return rows


def _route_matrix(project_root: Path) -> list[dict]:
    candidates = [
        project_root / "backend/src/palwakf_local_agents/app.py",
        project_root / "backend/src/palwakf_local_agents/local_agent_core/router.py",
        project_root / "backend/src/palwakf_local_agents/command_center/router.py",
        project_root / "backend/src/palwakf_local_agents/workspace_core/router.py",
        project_root / "backend/src/palwakf_local_agents/governed_operations/router.py",
        project_root / "backend/src/palwakf_local_agents/project_reader/router.py",
        project_root / "frontend/src/App.tsx",
    ]
    rows: list[dict] = []
    for path in candidates:
        rows.extend(_extract_route_lines(path, project_root))
    return rows


def _package_metadata(project_root: Path) -> dict:
    package_json = project_root / "frontend/package.json"
    pyproject = project_root / "pyproject.toml"
    payload: dict = {"frontend_package_json": None, "pyproject_present": pyproject.is_file()}
    if package_json.is_file():
        try:
            raw = json.loads(package_json.read_text(encoding="utf-8"))
            payload["frontend_package_json"] = {
                "name": raw.get("name"),
                "version": raw.get("version"),
                "scripts": sorted((raw.get("scripts") or {}).keys()),
                "dependencies": sorted((raw.get("dependencies") or {}).keys()),
                "dev_dependencies": sorted((raw.get("devDependencies") or {}).keys()),
            }
        except Exception as error:  # pragma: no cover
            payload["frontend_package_json_error"] = str(error)
    return payload


def _guardrails() -> dict:
    return {
        "tool_id": "local_project_reader_v1",
        "authority": "READ_ONLY_WORKSPACE_SCOPED",
        "source_mutation": "NONE",
        "database_write": "NONE",
        "model_execution": "NONE",
        "pilot_execution": "NOT_EXECUTED",
        "shell_execution": "BLOCKED_BY_DESIGN",
        "git_operations": "BLOCKED_BY_DESIGN",
        "external_web": "BLOCKED_BY_DESIGN",
        "platform_mutation": "BLOCKED_BY_DESIGN",
        "content_policy": "METADATA_AND_ROUTE_SUMMARY_ONLY_BY_DEFAULT",
    }


def mount_project_reader(app: FastAPI, project_root: Path) -> None:
    if getattr(app.state, "project_reader_mounted", False):
        raise RuntimeError("PROJECT_READER_ALREADY_MOUNTED")
    app.state.project_reader_project_root = project_root
    app.state.project_reader_mounted = True

    api = APIRouter(prefix="/api/v1/project-reader", tags=["project-reader"])

    @api.get("/health")
    def health() -> dict:
        return {
            "service": "local-project-reader",
            "status": "READ_ONLY_READY",
            "workspace_scope_required": True,
            "guardrails": _guardrails(),
        }

    @api.get("/workspaces/{workspace_id}/summary")
    def summary(workspace_id: str, include_routes: bool = Query(default=True)) -> dict:
        workspace_id = _safe_workspace_id(workspace_id)
        counts = _count_project_files(project_root)
        return {
            "workspace_id": workspace_id,
            "project_root_name": project_root.name,
            "status": "PASS",
            "mode": "READ_ONLY_WORKSPACE_SCOPED",
            "guardrails": _guardrails(),
            "counts": counts,
            "key_files": _key_file_records(project_root),
            "route_matrix": _route_matrix(project_root) if include_routes else [],
            "package_metadata": _package_metadata(project_root),
        }

    @api.get("/workspaces/{workspace_id}/route-matrix")
    def route_matrix(workspace_id: str) -> dict:
        workspace_id = _safe_workspace_id(workspace_id)
        return {"workspace_id": workspace_id, "status": "PASS", "mode": "READ_ONLY", "items": _route_matrix(project_root), "guardrails": _guardrails()}

    app.include_router(api)
