from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import tempfile
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["quality-gated-read-only-operations-wave1-v1"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "operations_wave1"
TASKS_FILE = RUNTIME_ROOT / "tasks.json"
MANIFESTS_FILE = RUNTIME_ROOT / "manifests.json"
RUNS_FILE = RUNTIME_ROOT / "runs.json"
REVIEWS_FILE = RUNTIME_ROOT / "reviews.jsonl"
EVIDENCE_FILE = RUNTIME_ROOT / "evidence.jsonl"
CHECKPOINTS_FILE = RUNTIME_ROOT / "checkpoints.json"

QUALITY_ROOT = PROJECT_ROOT / "runtime_state" / "operational_core_v1" / "tool_quality_lab"
BASELINES_FILE = QUALITY_ROOT / "quality_baselines.json"
QUARANTINES_FILE = QUALITY_ROOT / "quarantines.json"

_LOCK = threading.RLock()
MAX_FILES = 1200
MAX_SINGLE_FILE_BYTES = 1_000_000
MAX_RESULT_BYTES = 240_000
TOOL_CATALOG_VERSION = "1.0.0"

EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".dart_tool", ".idea", ".vscode", "runtime_state",
}
TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".dart", ".md", ".txt", ".json",
    ".yaml", ".yml", ".toml", ".html", ".css", ".scss", ".sql",
}

TOOLS = {
    "project_summary": {
        "label_ar": "ملخص المشروع",
        "description_ar": "ملخص بنيوي للمجلدات واللغات والملفات دون عرض محتوى حساس.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "project_summary",
    },
    "route_index": {
        "label_ar": "فهرس المسارات",
        "description_ar": "استخراج مسارات FastAPI وReact بصورة قرائية.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "route_index",
    },
    "component_index": {
        "label_ar": "فهرس المكونات",
        "description_ar": "استخراج مكونات React وWidgets في Flutter والكلاسات.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "component_index",
    },
    "symbol_index": {
        "label_ar": "فهرس الرموز",
        "description_ar": "استخراج الدوال والكلاسات والرموز من الملفات المدعومة.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "symbol_index",
    },
    "docs_index": {
        "label_ar": "فهرس الوثائق",
        "description_ar": "فهرسة بيانات الوثائق وعناوين النصوص المحلية دون OCR.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "docs_index",
    },
    "file_metadata": {
        "label_ar": "بيانات الملفات",
        "description_ar": "أحجام وامتدادات وبصمات ومسارات نسبية فقط.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "file_metadata",
    },
    "project_reader": {
        "label_ar": "قارئ المشروع",
        "description_ar": "قراءة منقحة لملف أو نطاق صغير داخل المشروع.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "project_reader",
    },
    "route_reader": {
        "label_ar": "قارئ المسارات",
        "description_ar": "عرض تفاصيل المسارات ومواقعها النسبية.",
        "quality_baseline_key": "native_code_index_contract",
        "result_kind": "route_reader",
    },
}

class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    goal: str = Field(min_length=3, max_length=4000)
    tool_id: str
    scope_relative: str = Field(default=".", max_length=500)
    operator_notes: str = Field(default="", max_length=2000)

class ApprovalRequest(BaseModel):
    approval_reference: str = Field(min_length=3, max_length=300)
    approved_by: str = Field(min_length=2, max_length=120)

class ResultReviewRequest(BaseModel):
    decision: str = Field(pattern="^(ACCEPT|RETURN|REJECT)$")
    notes: str = Field(default="", max_length=2000)
    reviewed_by: str = Field(min_length=2, max_length=120)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")

def _ensure_state() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        _atomic_write_json(TASKS_FILE, {"schema_version": "1.0.0", "tasks": {}})
    if not MANIFESTS_FILE.exists():
        _atomic_write_json(MANIFESTS_FILE, {"schema_version": "1.0.0", "manifests": {}})
    if not RUNS_FILE.exists():
        _atomic_write_json(RUNS_FILE, {"schema_version": "1.0.0", "runs": {}})
    if not CHECKPOINTS_FILE.exists():
        _atomic_write_json(CHECKPOINTS_FILE, {"schema_version": "1.0.0", "checkpoints": {}})

def _load_tasks() -> dict[str, Any]:
    _ensure_state()
    return _read_json(TASKS_FILE, {"schema_version": "1.0.0", "tasks": {}})

def _load_manifests() -> dict[str, Any]:
    _ensure_state()
    return _read_json(MANIFESTS_FILE, {"schema_version": "1.0.0", "manifests": {}})

def _load_runs() -> dict[str, Any]:
    _ensure_state()
    return _read_json(RUNS_FILE, {"schema_version": "1.0.0", "runs": {}})

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)

def _redact_text(text: str) -> tuple[str, bool]:
    original = text
    for workspace in {str(PROJECT_ROOT), str(PROJECT_ROOT).replace("\\", "/")}:
        text = text.replace(workspace, "<WORKSPACE>")
    patterns = [
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "<REDACTED_PRIVATE_KEY>"),
        (r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*['\"]?[^'\"\s,;]+", r"\1=<REDACTED>"),
        (r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}", r"\1 <REDACTED>"),
        (r"\b(?:ghp|github_pat|sk|xox[baprs])_[A-Za-z0-9_-]{8,}\b", "<REDACTED_TOKEN>"),
        (r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s\"']+", "<REDACTED_CONNECTION_STRING>"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return text, text != original

def _resolve_scope(relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("ABSOLUTE_SCOPE_NOT_ALLOWED")
    resolved = (PROJECT_ROOT / relative_path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("WORKSPACE_ESCAPE_BLOCKED") from exc
    if not resolved.exists():
        raise ValueError("SCOPE_NOT_FOUND")
    return resolved

def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()

def _iter_files(scope: Path):
    count = 0
    if scope.is_file():
        yield scope
        return
    for path in sorted(scope.rglob("*")):
        if count >= MAX_FILES:
            break
        if not path.is_file():
            continue
        relative_parts = path.relative_to(PROJECT_ROOT).parts
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative_parts):
            continue
        count += 1
        yield path

def _safe_read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    if path.stat().st_size > MAX_SINGLE_FILE_BYTES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")

def _quality_baseline(tool_id: str) -> dict[str, Any]:
    tool = TOOLS[tool_id]
    key = tool["quality_baseline_key"]
    baselines = _read_json(BASELINES_FILE, {"baselines": {}}).get("baselines", {})
    quarantines = _read_json(QUARANTINES_FILE, {"quarantines": {}}).get("quarantines", {})
    if key in quarantines:
        raise ValueError("QUALITY_BASELINE_QUARANTINED")
    baseline = baselines.get(key)
    if not baseline:
        raise ValueError("QUALITY_BASELINE_REQUIRED")
    if baseline.get("quality_result") not in {"QUALITY_ACCEPTED", "PASS_WITH_LIMITATIONS"}:
        raise ValueError("QUALITY_BASELINE_NOT_ELIGIBLE")
    return baseline

def _tool_catalog() -> list[dict[str, Any]]:
    result = []
    for tool_id, item in TOOLS.items():
        baseline = None
        status = "BLOCKED_PENDING_QUALITY_BASELINE"
        try:
            baseline = _quality_baseline(tool_id)
            status = "READY_WITH_LIMITATIONS" if baseline.get("quality_result") == "PASS_WITH_LIMITATIONS" else "READY"
        except ValueError:
            pass
        result.append({
            "tool_id": tool_id,
            **item,
            "operational_status": status,
            "baseline_id": baseline.get("baseline_id") if baseline else None,
            "limitations": baseline.get("limitations", []) if baseline else [],
        })
    return result

def _event(event_type: str, entity_id: str, details: dict[str, Any]) -> None:
    _append_jsonl(EVIDENCE_FILE, {
        "event_id": str(uuid.uuid4()),
        "occurred_at": _utc_now(),
        "event_type": event_type,
        "entity_id": entity_id,
        "details": details,
    })

def _get_task(task_id: str) -> dict[str, Any]:
    task = _load_tasks()["tasks"].get(task_id)
    if not task:
        raise ValueError("TASK_NOT_FOUND")
    return task

def _get_manifest(manifest_id: str) -> dict[str, Any]:
    manifest = _load_manifests()["manifests"].get(manifest_id)
    if not manifest:
        raise ValueError("MANIFEST_NOT_FOUND")
    return manifest

def _get_run(run_id: str) -> dict[str, Any]:
    run = _load_runs()["runs"].get(run_id)
    if not run:
        raise ValueError("RUN_NOT_FOUND")
    return run

def _create_task(request: CreateTaskRequest) -> dict[str, Any]:
    if request.tool_id not in TOOLS:
        raise ValueError("UNKNOWN_TOOL_ID")
    scope = _resolve_scope(request.scope_relative)
    task_id = str(uuid.uuid4())
    task = {
        "task_id": task_id,
        "title": request.title,
        "goal": request.goal,
        "tool_id": request.tool_id,
        "scope_relative": _relative(scope),
        "operator_notes": request.operator_notes,
        "status": "DRAFT",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "manifest_id": None,
        "run_id": None,
        "approval_reference": None,
        "approved_by": None,
    }
    with _LOCK:
        state = _load_tasks()
        state["tasks"][task_id] = task
        _atomic_write_json(TASKS_FILE, state)
    _event("TASK_CREATED", task_id, {"status": "DRAFT", "tool_id": request.tool_id})
    return task

def _set_task_status(task_id: str, expected: set[str], new_status: str) -> dict[str, Any]:
    with _LOCK:
        state = _load_tasks()
        task = state["tasks"].get(task_id)
        if not task:
            raise ValueError("TASK_NOT_FOUND")
        if task["status"] not in expected:
            raise ValueError(f"INVALID_TASK_TRANSITION_FROM_{task['status']}")
        task["status"] = new_status
        task["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, state)
    _event("TASK_STATUS_CHANGED", task_id, {"status": new_status})
    return task

def _prepare_manifest(task_id: str) -> dict[str, Any]:
    task = _get_task(task_id)
    if task["status"] not in {"DRAFT", "READY_FOR_REVIEW"}:
        raise ValueError("TASK_NOT_READY_FOR_MANIFEST")
    baseline = _quality_baseline(task["tool_id"])
    scope = _resolve_scope(task["scope_relative"])

    core = {
        "task_id": task_id,
        "tool_id": task["tool_id"],
        "tool_catalog_version": TOOL_CATALOG_VERSION,
        "quality_baseline_key": TOOLS[task["tool_id"]]["quality_baseline_key"],
        "quality_baseline_id": baseline["baseline_id"],
        "quality_result": baseline["quality_result"],
        "scope_relative": _relative(scope),
        "allowed_operation": "native_read_only",
        "network_policy": "blocked",
        "write_policy": "blocked",
        "shell_policy": "blocked",
        "git_policy": "blocked",
        "timeout_seconds": 45,
        "max_files": MAX_FILES,
        "max_result_bytes": MAX_RESULT_BYTES,
        "input_hash": _sha256_json({
            "title": task["title"],
            "goal": task["goal"],
            "tool_id": task["tool_id"],
            "scope_relative": task["scope_relative"],
        }),
    }
    manifest_id = str(uuid.uuid4())
    manifest = {
        "manifest_id": manifest_id,
        **core,
        "manifest_sha256": _sha256_json(core),
        "created_at": _utc_now(),
        "status": "PREPARED",
    }
    with _LOCK:
        manifests = _load_manifests()
        manifests["manifests"][manifest_id] = manifest
        _atomic_write_json(MANIFESTS_FILE, manifests)
        tasks = _load_tasks()
        tasks["tasks"][task_id]["manifest_id"] = manifest_id
        tasks["tasks"][task_id]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)
    _event("MANIFEST_PREPARED", manifest_id, {
        "task_id": task_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "baseline_id": baseline["baseline_id"],
    })
    return manifest

def _approve_task(task_id: str, request: ApprovalRequest) -> dict[str, Any]:
    with _LOCK:
        tasks = _load_tasks()
        task = tasks["tasks"].get(task_id)
        if not task:
            raise ValueError("TASK_NOT_FOUND")
        if task["status"] != "READY_FOR_REVIEW":
            raise ValueError("TASK_NOT_READY_FOR_APPROVAL")
        if not task.get("manifest_id"):
            raise ValueError("MANIFEST_REQUIRED")
        manifest = _get_manifest(task["manifest_id"])
        if manifest["status"] != "PREPARED":
            raise ValueError("MANIFEST_NOT_PREPARED")
        task["status"] = "APPROVED_FOR_READ_ONLY_RUN"
        task["approval_reference"] = request.approval_reference
        task["approved_by"] = request.approved_by
        task["updated_at"] = _utc_now()
        tasks["tasks"][task_id] = task
        _atomic_write_json(TASKS_FILE, tasks)

        manifests = _load_manifests()
        manifests["manifests"][manifest["manifest_id"]]["status"] = "APPROVED"
        manifests["manifests"][manifest["manifest_id"]]["approval_reference"] = request.approval_reference
        manifests["manifests"][manifest["manifest_id"]]["approved_by"] = request.approved_by
        manifests["manifests"][manifest["manifest_id"]]["approved_at"] = _utc_now()
        _atomic_write_json(MANIFESTS_FILE, manifests)
    _event("TASK_APPROVED", task_id, {
        "manifest_id": task["manifest_id"],
        "approval_reference": request.approval_reference,
    })
    return task

def _verify_manifest_current(task: dict[str, Any], manifest: dict[str, Any]) -> None:
    baseline = _quality_baseline(task["tool_id"])
    if baseline["baseline_id"] != manifest["quality_baseline_id"]:
        raise ValueError("STALE_MANIFEST_BASELINE_CHANGED")
    if manifest["tool_catalog_version"] != TOOL_CATALOG_VERSION:
        raise ValueError("STALE_MANIFEST_TOOL_CATALOG_CHANGED")
    expected_input = _sha256_json({
        "title": task["title"],
        "goal": task["goal"],
        "tool_id": task["tool_id"],
        "scope_relative": task["scope_relative"],
    })
    if expected_input != manifest["input_hash"]:
        raise ValueError("STALE_MANIFEST_INPUT_CHANGED")

def _python_route_records(path: Path, source: str) -> list[dict[str, Any]]:
    records = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return records
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            func = decorator.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id in {"app", "router"}
                and isinstance(decorator.args[0], ast.Constant)
            ):
                records.append({
                    "method": func.attr.upper(),
                    "path": str(decorator.args[0].value),
                    "handler": node.name,
                    "source": _relative(path),
                    "line": node.lineno,
                })
    return records

def _execute_tool(tool_id: str, scope: Path) -> dict[str, Any]:
    files = list(_iter_files(scope))

    if tool_id == "file_metadata":
        items = []
        for path in files:
            data = path.read_bytes()
            items.append({
                "path": _relative(path),
                "size_bytes": len(data),
                "extension": path.suffix.lower(),
                "sha256": _sha256_bytes(data),
            })
        return {"files": items, "file_count": len(items), "truncated": len(files) >= MAX_FILES}

    if tool_id == "project_summary":
        extensions = Counter(path.suffix.lower() or "<none>" for path in files)
        top_dirs = Counter(path.relative_to(scope).parts[0] if path.relative_to(scope).parts else "." for path in files)
        return {
            "scope": _relative(scope),
            "file_count": len(files),
            "extensions": dict(extensions.most_common(30)),
            "top_level_areas": dict(top_dirs.most_common(30)),
            "supported_text_files": sum(1 for path in files if path.suffix.lower() in TEXT_EXTENSIONS),
        }

    if tool_id in {"route_index", "route_reader"}:
        routes = []
        for path in files:
            source = _safe_read_text(path)
            if source is None:
                continue
            if path.suffix.lower() == ".py":
                routes.extend(_python_route_records(path, source))
            if path.suffix.lower() in {".tsx", ".jsx", ".ts", ".js"}:
                for match in re.finditer(r'path\s*=\s*["\']([^"\']+)["\']', source):
                    routes.append({
                        "method": "UI",
                        "path": match.group(1),
                        "handler": None,
                        "source": _relative(path),
                        "line": source.count("\n", 0, match.start()) + 1,
                    })
        return {"routes": routes, "route_count": len(routes)}

    if tool_id == "component_index":
        components = []
        for path in files:
            source = _safe_read_text(path)
            if source is None:
                continue
            suffix = path.suffix.lower()
            if suffix in {".tsx", ".jsx", ".ts", ".js"}:
                names = set()
                names.update(re.findall(r"\bexport\s+function\s+([A-Z][A-Za-z0-9_]*)\s*\(", source))
                names.update(re.findall(r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*[:=]", source))
                for name in sorted(names):
                    components.append({"name": name, "kind": "react_component", "source": _relative(path)})
            elif suffix == ".dart":
                for name in re.findall(r"class\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+(?:StatelessWidget|StatefulWidget)", source):
                    components.append({"name": name, "kind": "flutter_widget", "source": _relative(path)})
            elif suffix == ".py":
                try:
                    tree = ast.parse(source, filename=str(path))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            components.append({"name": node.name, "kind": "python_class", "source": _relative(path), "line": node.lineno})
                except SyntaxError:
                    pass
        return {"components": components, "component_count": len(components)}

    if tool_id == "symbol_index":
        symbols = []
        for path in files:
            source = _safe_read_text(path)
            if source is None:
                continue
            if path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(source, filename=str(path))
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            symbols.append({
                                "name": node.name,
                                "kind": type(node).__name__,
                                "source": _relative(path),
                                "line": node.lineno,
                            })
                except SyntaxError:
                    pass
            elif path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".dart"}:
                for match in re.finditer(r"\b(?:class|function|const)\s+([A-Za-z_][A-Za-z0-9_]*)", source):
                    symbols.append({
                        "name": match.group(1),
                        "kind": "text_symbol",
                        "source": _relative(path),
                        "line": source.count("\n", 0, match.start()) + 1,
                    })
        return {"symbols": symbols, "symbol_count": len(symbols)}

    if tool_id == "docs_index":
        docs = []
        for path in files:
            if path.suffix.lower() not in {".md", ".txt", ".pdf", ".docx"}:
                continue
            title = path.stem
            if path.suffix.lower() in {".md", ".txt"}:
                source = _safe_read_text(path) or ""
                for line in source.splitlines()[:30]:
                    stripped = line.strip().lstrip("#").strip()
                    if stripped:
                        title = stripped[:160]
                        break
            docs.append({
                "path": _relative(path),
                "title": title,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "content_read": path.suffix.lower() in {".md", ".txt"},
                "ocr_used": False,
            })
        return {"documents": docs, "document_count": len(docs)}

    if tool_id == "project_reader":
        if scope.is_file():
            source = _safe_read_text(scope)
            if source is None:
                return {"path": _relative(scope), "readable_text": False, "size_bytes": scope.stat().st_size}
            redacted, changed = _redact_text(source[:80_000])
            return {
                "path": _relative(scope),
                "readable_text": True,
                "redacted": changed,
                "excerpt": redacted,
                "truncated": len(source) > 80_000,
            }
        return {
            "scope": _relative(scope),
            "entries": [{"path": _relative(path), "size_bytes": path.stat().st_size} for path in files[:250]],
            "entry_count": min(len(files), 250),
            "truncated": len(files) > 250,
        }

    raise ValueError("TOOL_IMPLEMENTATION_NOT_FOUND")

def _run_task(task_id: str) -> dict[str, Any]:
    task = _get_task(task_id)
    if task["status"] != "APPROVED_FOR_READ_ONLY_RUN":
        raise ValueError("UNAPPROVED_TASK_EXECUTION_BLOCKED")
    manifest = _get_manifest(task["manifest_id"])
    if manifest["status"] != "APPROVED":
        raise ValueError("UNAPPROVED_MANIFEST_EXECUTION_BLOCKED")
    _verify_manifest_current(task, manifest)

    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    with _LOCK:
        tasks = _load_tasks()
        tasks["tasks"][task_id]["status"] = "RUNNING"
        tasks["tasks"][task_id]["run_id"] = run_id
        tasks["tasks"][task_id]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)
    _event("RUN_STARTED", run_id, {"task_id": task_id, "manifest_id": manifest["manifest_id"]})

    started = time.monotonic()
    try:
        scope = _resolve_scope(task["scope_relative"])
        result = _execute_tool(task["tool_id"], scope)
        redacted_json, redacted = _redact_text(json.dumps(result, ensure_ascii=False, sort_keys=True))
        encoded = redacted_json.encode("utf-8")
        truncated = len(encoded) > MAX_RESULT_BYTES
        if truncated:
            encoded = encoded[:MAX_RESULT_BYTES]
            redacted_json = encoded.decode("utf-8", errors="ignore")
        result_hash = _sha256_bytes(encoded)
        run = {
            "run_id": run_id,
            "task_id": task_id,
            "manifest_id": manifest["manifest_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "tool_id": task["tool_id"],
            "status": "HUMAN_RESULT_REVIEW",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "result_sha256": result_hash,
            "redaction_applied": redacted,
            "result_truncated": truncated,
            "result": json.loads(redacted_json) if not truncated else {"truncated_json_excerpt": redacted_json},
            "source_write": "none",
            "network_runtime": "none",
            "shell": "none",
            "git": "none",
            "automatic_retry": False,
        }
        with _LOCK:
            runs = _load_runs()
            runs["runs"][run_id] = run
            _atomic_write_json(RUNS_FILE, runs)
            tasks = _load_tasks()
            tasks["tasks"][task_id]["status"] = "HUMAN_RESULT_REVIEW"
            tasks["tasks"][task_id]["updated_at"] = _utc_now()
            _atomic_write_json(TASKS_FILE, tasks)
        _event("RUN_COMPLETED", run_id, {
            "task_id": task_id,
            "result_sha256": result_hash,
            "redaction_applied": redacted,
            "duration_ms": run["duration_ms"],
        })
        return run
    except Exception as exc:
        with _LOCK:
            tasks = _load_tasks()
            tasks["tasks"][task_id]["status"] = "FAILED"
            tasks["tasks"][task_id]["updated_at"] = _utc_now()
            _atomic_write_json(TASKS_FILE, tasks)
        _event("RUN_FAILED", run_id, {"task_id": task_id, "error_class": type(exc).__name__, "error": str(exc)})
        raise

def _review_result(run_id: str, request: ResultReviewRequest) -> dict[str, Any]:
    run = _get_run(run_id)
    if run["status"] != "HUMAN_RESULT_REVIEW":
        raise ValueError("RUN_NOT_READY_FOR_RESULT_REVIEW")
    task = _get_task(run["task_id"])

    status_map = {
        "ACCEPT": "ACCEPTED_RESULT",
        "RETURN": "RETURNED_FOR_REVIEW",
        "REJECT": "REJECTED_RESULT",
    }
    new_status = status_map[request.decision]
    review = {
        "review_id": str(uuid.uuid4()),
        "run_id": run_id,
        "task_id": run["task_id"],
        "decision": request.decision,
        "notes": request.notes,
        "reviewed_by": request.reviewed_by,
        "reviewed_at": _utc_now(),
    }
    with _LOCK:
        runs = _load_runs()
        runs["runs"][run_id]["status"] = new_status
        runs["runs"][run_id]["review"] = review
        _atomic_write_json(RUNS_FILE, runs)

        tasks = _load_tasks()
        tasks["tasks"][task["task_id"]]["status"] = new_status
        tasks["tasks"][task["task_id"]]["updated_at"] = _utc_now()
        _atomic_write_json(TASKS_FILE, tasks)

        if request.decision == "ACCEPT":
            checkpoints = _read_json(CHECKPOINTS_FILE, {"schema_version": "1.0.0", "checkpoints": {}})
            checkpoint_id = str(uuid.uuid4())
            checkpoints["checkpoints"][checkpoint_id] = {
                "checkpoint_id": checkpoint_id,
                "task_id": task["task_id"],
                "run_id": run_id,
                "result_sha256": run["result_sha256"],
                "manifest_sha256": run["manifest_sha256"],
                "created_at": _utc_now(),
                "snapshot_type": "metadata_only",
                "source_snapshot": False,
            }
            _atomic_write_json(CHECKPOINTS_FILE, checkpoints)
            review["checkpoint_id"] = checkpoint_id

    _append_jsonl(REVIEWS_FILE, review)
    _event("RESULT_REVIEWED", run_id, {"decision": request.decision, "reviewed_by": request.reviewed_by})
    return review

def _dashboard() -> dict[str, Any]:
    tasks = list(_load_tasks()["tasks"].values())
    runs = list(_load_runs()["runs"].values())
    return {
        "result": "PASS",
        "summary": {
            "drafts": sum(1 for item in tasks if item["status"] == "DRAFT"),
            "ready_for_review": sum(1 for item in tasks if item["status"] == "READY_FOR_REVIEW"),
            "approved": sum(1 for item in tasks if item["status"] == "APPROVED_FOR_READ_ONLY_RUN"),
            "result_review": sum(1 for item in tasks if item["status"] == "HUMAN_RESULT_REVIEW"),
            "accepted_results": sum(1 for item in tasks if item["status"] == "ACCEPTED_RESULT"),
        },
        "tasks": sorted(tasks, key=lambda item: item["updated_at"], reverse=True)[:50],
        "runs": sorted(runs, key=lambda item: item["completed_at"], reverse=True)[:30],
        "tools": _tool_catalog(),
    }

def _http_error(exc: Exception) -> HTTPException:
    message = str(exc)
    status = 404 if message.endswith("_NOT_FOUND") else 409
    if "BLOCKED" in message or "REQUIRED" in message or "UNAPPROVED" in message or "STALE" in message:
        status = 403
    return HTTPException(status_code=status, detail=message)

@router.get("/api/v1/operational-core/operations-wave1/health")
def health() -> dict[str, Any]:
    _ensure_state()
    return {
        "result": "PASS",
        "mode": "quality_gated_end_to_end_native_read_only_execution",
        "tool_count": len(TOOLS),
        "model_inference": "none",
        "shell": "blocked",
        "git": "blocked",
        "network_runtime": "blocked",
        "source_write": "blocked",
        "automatic_retry": "blocked",
        "human_approval": "required",
        "human_result_review": "required",
    }

@router.get("/api/v1/operational-core/operations-wave1/dashboard")
def dashboard() -> dict[str, Any]:
    return _dashboard()

@router.get("/api/v1/operational-core/operations-wave1/tools")
def tools() -> dict[str, Any]:
    return {"result": "PASS", "tools": _tool_catalog()}

@router.get("/api/v1/operational-core/operations-wave1/tasks")
def tasks() -> dict[str, Any]:
    return _load_tasks()

@router.get("/api/v1/operational-core/operations-wave1/manifests")
def manifests() -> dict[str, Any]:
    return _load_manifests()

@router.get("/api/v1/operational-core/operations-wave1/runs")
def runs() -> dict[str, Any]:
    return _load_runs()

@router.get("/api/v1/operational-core/operations-wave1/evidence")
def evidence(limit: int = 200) -> dict[str, Any]:
    if not EVIDENCE_FILE.is_file():
        return {"result": "PASS", "events": []}
    lines = EVIDENCE_FILE.read_text(encoding="utf-8").splitlines()
    return {"result": "PASS", "events": [json.loads(line) for line in lines[-max(1, min(limit, 500)):] if line.strip()]}

@router.get("/api/v1/operational-core/operations-wave1/checkpoints")
def checkpoints() -> dict[str, Any]:
    _ensure_state()
    return _read_json(CHECKPOINTS_FILE, {"schema_version": "1.0.0", "checkpoints": {}})

@router.get("/api/v1/operational-core/operations-wave1/governance")
def governance() -> dict[str, Any]:
    return {
        "result": "PASS",
        "state_machine": [
            "DRAFT", "READY_FOR_REVIEW", "APPROVED_FOR_READ_ONLY_RUN",
            "RUNNING", "HUMAN_RESULT_REVIEW", "ACCEPTED_RESULT",
            "RETURNED_FOR_REVIEW", "REJECTED_RESULT", "FAILED",
        ],
        "boundaries": health(),
        "governance_pages": [
            "/agent-console/operations/governance",
            "/agent-console/operations/manifests",
            "/agent-console/operations/evidence",
        ],
    }

@router.post("/api/v1/operational-core/operations-wave1/tasks")
def create_task(request: CreateTaskRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "task": _create_task(request)}
    except Exception as exc:
        raise _http_error(exc) from exc

@router.post("/api/v1/operational-core/operations-wave1/tasks/{task_id}/submit")
def submit_task(task_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "task": _set_task_status(task_id, {"DRAFT", "RETURNED_FOR_REVIEW"}, "READY_FOR_REVIEW")}
    except Exception as exc:
        raise _http_error(exc) from exc

@router.post("/api/v1/operational-core/operations-wave1/tasks/{task_id}/prepare-manifest")
def prepare_manifest(task_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "manifest": _prepare_manifest(task_id)}
    except Exception as exc:
        raise _http_error(exc) from exc

@router.post("/api/v1/operational-core/operations-wave1/tasks/{task_id}/approve")
def approve_task(task_id: str, request: ApprovalRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "task": _approve_task(task_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc

@router.post("/api/v1/operational-core/operations-wave1/tasks/{task_id}/run")
def run_task(task_id: str) -> dict[str, Any]:
    try:
        return {"result": "PASS", "run": _run_task(task_id)}
    except Exception as exc:
        raise _http_error(exc) from exc

@router.post("/api/v1/operational-core/operations-wave1/runs/{run_id}/review")
def review_result(run_id: str, request: ResultReviewRequest) -> dict[str, Any]:
    try:
        return {"result": "PASS", "review": _review_result(run_id, request)}
    except Exception as exc:
        raise _http_error(exc) from exc
