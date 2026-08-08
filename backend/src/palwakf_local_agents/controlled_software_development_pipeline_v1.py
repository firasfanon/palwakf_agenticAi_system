from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from palwakf_local_agents.operational_core_v1.codebase_index import CodebaseIndexer
from palwakf_local_agents import quality_accepted_tools_goal_planner_binding_v1 as planner

CONTRACT_ID = "CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_V1"
FIRST_CANDIDATE_PROFILE = "READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1"
FIRST_CANDIDATE_KEY = "FIRST-CANDIDATE-PATCH-V1"
TOOL_ID = "native-code-index"
API_PREFIX = "/api/v1/operational-core/development-pipeline"
CANDIDATE_ENDPOINT = "/api/v1/operational-core/development-diagnostic/health"
_LOCK = threading.RLock()

class GenerateCandidateRequest(BaseModel):
    candidate_key: str = Field(default=FIRST_CANDIDATE_KEY, min_length=8, max_length=180)
    goal_id: str = Field(default="GOAL-FIRST-CANDIDATE-PATCH-001", min_length=3, max_length=180)
    goal_text: str = Field(default="إضافة نقطة تشخيص مقروءة فقط لمسار التطوير المحكوم", min_length=10, max_length=1000)
    profile_id: str = FIRST_CANDIDATE_PROFILE
    provider_id: str = "deterministic-template-v1"
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    confirm_candidate_workspace_only: bool

class ReviewRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    note: str = Field(default="", max_length=1200)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + "\n")


def _safe_relative(value: str) -> PurePosixPath:
    normalized = PurePosixPath(value.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or not normalized.parts:
        raise RuntimeError("UNSAFE_CANDIDATE_RELATIVE_PATH")
    return normalized


def _copytree_filtered(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
    )


def _manifest_digest(root: Path) -> dict[str, Any]:
    records: list[tuple[str, int, str]] = []
    if not root.exists():
        return {"file_count": 0, "total_bytes": 0, "digest": _sha256_bytes(b"[]")}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            data = path.read_bytes()
            rel = path.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        records.append((rel, len(data), _sha256_bytes(data)))
    payload = json.dumps(records, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "file_count": len(records),
        "total_bytes": sum(item[1] for item in records),
        "digest": _sha256_bytes(payload),
    }


class ControlledSoftwareDevelopmentPipelineService:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.runtime_root = self.project_root / "runtime_state/operational_core_v1/controlled_software_development_pipeline_v1"
        self.candidates_root = self.runtime_root / "candidates"
        self.events_file = self.runtime_root / "events.jsonl"
        self.reviews_file = self.runtime_root / "reviews.jsonl"
        self.latest_file = self.runtime_root / "latest.json"

    def contract(self) -> dict[str, Any]:
        return {
            "contract_id": CONTRACT_ID,
            "first_candidate_profile": FIRST_CANDIDATE_PROFILE,
            "workflow": [
                "GOAL", "PLAN", "PROJECT_UNDERSTANDING", "CANDIDATE_WORKSPACE",
                "CONTROLLED_FILE_EDIT", "DIRECT_ARGV_TESTS", "DIFF_REVIEW",
                "HUMAN_REVIEW", "SEPARATE_CONTROLLED_APPLY_AUTHORIZATION",
            ],
            "candidate_write_scope": "runtime_state/operational_core_v1/controlled_software_development_pipeline_v1/candidates",
            "source_apply_endpoint": "ABSENT_BY_DESIGN_V1",
            "boundaries": {
                "production_execution": "NOT_AUTHORIZED",
                "real_source_write_by_candidate_generation": "NONE",
                "candidate_workspace_write": "ALLOWED",
                "model_execution": "NONE",
                "shell": "BLOCKED",
                "git": "BLOCKED",
                "network": "BLOCKED",
                "database_write": "NONE",
                "self_apply": "BLOCKED",
                "test_runner": "DIRECT_ARGV_PYTHON_ALLOWLIST_ONLY",
                "human_authority": "REQUIRED",
            },
        }

    def providers(self) -> dict[str, Any]:
        return {
            "providers": [
                {
                    "provider_id": "deterministic-template-v1",
                    "state": "ENABLED_FOR_FIRST_PILOT",
                    "model_execution": False,
                    "purpose": "Generate the governed diagnostic endpoint candidate deterministically.",
                },
                {
                    "provider_id": "ollama-coding",
                    "state": "DISABLED_REQUIRES_SEPARATE_AUTHORIZATION",
                    "model_execution": False,
                },
                {
                    "provider_id": "openai-compatible-coding",
                    "state": "DISABLED_REQUIRES_SEPARATE_AUTHORIZATION",
                    "model_execution": False,
                },
            ]
        }

    def health(self) -> dict[str, Any]:
        quality = planner.load_quality_snapshot().get("tools", {}).get(TOOL_ID, {})
        return {
            "status": "ok",
            "contract_id": CONTRACT_ID,
            "tool_id": TOOL_ID,
            "quality_state": quality.get("quality_state", "UNASSESSED"),
            "planner_state": quality.get("planner_state", "BLOCKED_UNASSESSED"),
            "candidate_generation": "AVAILABLE_WITH_HUMAN_AUTHORITY",
            "source_apply": "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
            "model_execution": "NONE",
            "shell_git_network": "BLOCKED",
        }

    def _quality_gate(self) -> dict[str, Any]:
        quality = planner.load_quality_snapshot().get("tools", {}).get(TOOL_ID)
        required = {"quality_state": "QUALITY_ACCEPTED", "planner_state": "SELECTABLE", "baseline_present": True}
        observed = {key: quality.get(key) if isinstance(quality, dict) else None for key in required}
        if observed != required:
            raise HTTPException(status_code=409, detail={"code": "QUALITY_GATE_NOT_SATISFIED", "required": required, "observed": observed})
        return {
            "tool_id": TOOL_ID,
            "quality_state": quality.get("quality_state"),
            "planner_state": quality.get("planner_state"),
            "score": quality.get("score"),
            "baseline_id": quality.get("baseline_id"),
            "suite_id": quality.get("suite_id"),
        }

    def _candidate_id(self, candidate_key: str) -> str:
        return "cand-" + _sha256_bytes(candidate_key.encode("utf-8"))[:16].lower()

    def _candidate_dir(self, candidate_id: str) -> Path:
        return self.candidates_root / candidate_id

    def _manifest_path(self, candidate_id: str) -> Path:
        return self._candidate_dir(candidate_id) / "candidate_manifest.json"

    def _load_manifest(self, candidate_id: str) -> dict[str, Any]:
        path = self._manifest_path(candidate_id)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="CANDIDATE_NOT_FOUND")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_candidates(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        records: list[dict[str, Any]] = []
        if self.candidates_root.is_dir():
            for path in sorted(self.candidates_root.glob("*/candidate_manifest.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:limit]:
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                records.append(self._public_manifest(record, include_diff=False))
        return {"candidates": records, "count": len(records), "limit": limit}

    def latest(self) -> dict[str, Any]:
        if not self.latest_file.is_file():
            return {"available": False, "message": "NO_CANDIDATE_GENERATED"}
        candidate_id = json.loads(self.latest_file.read_text(encoding="utf-8")).get("candidate_id")
        if not candidate_id:
            return {"available": False, "message": "NO_CANDIDATE_GENERATED"}
        return {"available": True, "candidate": self.get_candidate(candidate_id)}

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._public_manifest(self._load_manifest(candidate_id), include_diff=True)

    def _public_manifest(self, manifest: dict[str, Any], *, include_diff: bool) -> dict[str, Any]:
        public = {key: value for key, value in manifest.items() if key not in {"internal"}}
        if not include_diff:
            public.pop("unified_diff", None)
        return public

    def _diagnostic_module(self) -> str:
        return '''from __future__ import annotations\n\nfrom typing import Any\nfrom fastapi import APIRouter, FastAPI\n\nCONTRACT_ID = "READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1"\nAPI_PREFIX = "/api/v1/operational-core/development-diagnostic"\n\ndef create_router() -> APIRouter:\n    router = APIRouter(prefix=API_PREFIX, tags=["development-diagnostic-v1"])\n\n    @router.get("/health")\n    def health() -> dict[str, Any]:\n        return {\n            "status": "ok",\n            "contract_id": CONTRACT_ID,\n            "read_only": True,\n            "source_mutation": "NONE",\n            "model_execution": "NONE",\n            "shell_git_network": "BLOCKED",\n            "production_execution": "NOT_AUTHORIZED",\n        }\n\n    return router\n\ndef install_development_diagnostic_v1(app: FastAPI) -> None:\n    state = getattr(app, "state", None)\n    if state is not None and getattr(state, "development_diagnostic_v1_installed", False):\n        return\n    app.include_router(create_router())\n    if state is not None:\n        state.development_diagnostic_v1_installed = True\n'''

    def _patch_app(self, text: str) -> str:
        import_line = "from palwakf_local_agents.development_diagnostic_v1 import install_development_diagnostic_v1"
        call_line = "install_development_diagnostic_v1(app)"
        if import_line not in text:
            lines = text.splitlines(keepends=True)
            insert_at = 0
            for index, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import ") or not line.strip() or line.startswith("from __future__"):
                    insert_at = index + 1
                    continue
                break
            lines.insert(insert_at, import_line + "\n")
            text = "".join(lines)
        if call_line not in text:
            lines = text.splitlines(keepends=True)
            matches = [index for index, line in enumerate(lines) if "resolved_project_root =" in line]
            if len(matches) != 1:
                raise RuntimeError("CANDIDATE_APP_RESOLVED_PROJECT_ROOT_NOT_EXACTLY_ONCE")
            index = matches[0]
            indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
            lines.insert(index + 1, indent + call_line + "\n")
            text = "".join(lines)
        if text.count(import_line) != 1 or text.count(call_line) != 1:
            raise RuntimeError("CANDIDATE_APP_PATCH_NOT_IDEMPOTENT")
        compile(text, "candidate-app.py", "exec")
        return text

    def _write_candidate_file(self, workspace: Path, relative: str, content: str) -> Path:
        rel = _safe_relative(relative)
        allowed = {
            PurePosixPath("backend/src/palwakf_local_agents/app.py"),
            PurePosixPath("backend/src/palwakf_local_agents/development_diagnostic_v1.py"),
            PurePosixPath("candidate_test.py"),
        }
        if rel not in allowed:
            raise RuntimeError("CANDIDATE_EDITOR_TARGET_NOT_ALLOWED=" + rel.as_posix())
        target = workspace.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target

    def _candidate_test_script(self) -> str:
        return '''from __future__ import annotations\nimport asyncio, json, os, sys\nfrom pathlib import Path\nroot=Path(__file__).resolve().parent\nsys.path.insert(0,str(root/"backend/src"))\nos.environ["PALWAKF_LOCAL_AGENTS_SOURCE_ROOT"]=str(root)\nfrom palwakf_local_agents.app import app\npath="/api/v1/operational-core/development-diagnostic/health"\nopenapi=app.openapi().get("paths",{})\nassert "get" in openapi.get(path,{}), openapi.get(path)\nasync def request():\n    messages=[]; consumed=False\n    async def receive():\n        nonlocal consumed\n        if not consumed:\n            consumed=True; return {"type":"http.request","body":b"","more_body":False}\n        return {"type":"http.disconnect"}\n    async def send(message): messages.append(message)\n    scope={"type":"http","asgi":{"version":"3.0","spec_version":"2.3"},"http_version":"1.1","method":"GET","scheme":"http","path":path,"raw_path":path.encode(),"query_string":b"","root_path":"","headers":[(b"host",b"candidate-test")],"client":("127.0.0.1",58001),"server":("candidate-test",80),"state":{}}\n    await app(scope,receive,send)\n    status=None; body=[]\n    for message in messages:\n        if message["type"]=="http.response.start": status=int(message["status"])\n        elif message["type"]=="http.response.body": body.append(message.get("body",b""))\n    assert status==200,status\n    payload=json.loads(b"".join(body).decode())\n    assert payload["read_only"] is True\n    assert payload["source_mutation"]=="NONE"\n    return payload\npayload=asyncio.run(request())\nprint("CANDIDATE_APP_IMPORT=PASS")\nprint("CANDIDATE_OPENAPI=PASS")\nprint("CANDIDATE_HTTP=200")\nprint("CANDIDATE_BOUNDARIES=PASS")\nprint(json.dumps(payload,sort_keys=True))\n'''

    def _create_export(self, candidate_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        export_path = candidate_dir / "candidate_export.zip"
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("candidate_manifest.json", json.dumps(self._public_manifest(manifest, include_diff=True), ensure_ascii=False, indent=2))
            archive.writestr("candidate.patch", manifest["unified_diff"])
            for rel in manifest["target_files"]:
                path = candidate_dir / "workspace" / rel
                if path.is_file():
                    archive.write(path, arcname="workspace/" + rel)
        return {"filename": export_path.name, "size_bytes": export_path.stat().st_size, "sha256": _sha256_file(export_path)}

    def generate(self, request: GenerateCandidateRequest) -> dict[str, Any]:
        if request.profile_id != FIRST_CANDIDATE_PROFILE:
            raise HTTPException(status_code=422, detail="PROFILE_NOT_AUTHORIZED")
        if request.provider_id != "deterministic-template-v1":
            raise HTTPException(status_code=422, detail="MODEL_PROVIDER_NOT_AUTHORIZED")
        if request.human_authority_confirmed is not True:
            raise HTTPException(status_code=422, detail="HUMAN_AUTHORITY_CONFIRMATION_REQUIRED")
        if request.confirm_candidate_workspace_only is not True:
            raise HTTPException(status_code=422, detail="CANDIDATE_WORKSPACE_CONFIRMATION_REQUIRED")

        quality = self._quality_gate()
        candidate_id = self._candidate_id(request.candidate_key)
        candidate_dir = self._candidate_dir(candidate_id)
        manifest_path = self._manifest_path(candidate_id)

        with _LOCK:
            if manifest_path.is_file():
                return {"result": "ALREADY_GENERATED", "idempotent_reuse": True, "candidate": self.get_candidate(candidate_id)}

            source_package = self.project_root / "backend/src/palwakf_local_agents"
            source_frontend_dist = self.project_root / "frontend/dist"
            source_app = source_package / "app.py"
            if not source_app.is_file():
                raise HTTPException(status_code=409, detail="SOURCE_APP_NOT_FOUND")

            source_before = {
                "backend_package": _manifest_digest(source_package),
                "frontend_dist": _manifest_digest(source_frontend_dist),
            }

            workspace = candidate_dir / "workspace"
            candidate_backend_package = workspace / "backend/src/palwakf_local_agents"
            _copytree_filtered(source_package, candidate_backend_package)
            if source_frontend_dist.is_dir():
                _copytree_filtered(source_frontend_dist, workspace / "frontend/dist")
            else:
                (workspace / "frontend/dist").mkdir(parents=True, exist_ok=True)
                (workspace / "frontend/dist/index.html").write_text("<!doctype html><html><body></body></html>", encoding="utf-8")
            for name in ("agents", "docs", "runtime_state"):
                (workspace / name).mkdir(parents=True, exist_ok=True)

            original_app = source_app.read_text(encoding="utf-8")
            candidate_app = self._patch_app(original_app)
            diagnostic = self._diagnostic_module()
            self._write_candidate_file(workspace, "backend/src/palwakf_local_agents/app.py", candidate_app)
            self._write_candidate_file(workspace, "backend/src/palwakf_local_agents/development_diagnostic_v1.py", diagnostic)
            test_script = self._write_candidate_file(workspace, "candidate_test.py", self._candidate_test_script())

            app_diff = "".join(difflib.unified_diff(original_app.splitlines(True), candidate_app.splitlines(True), fromfile="a/backend/src/palwakf_local_agents/app.py", tofile="b/backend/src/palwakf_local_agents/app.py"))
            module_diff = "".join(difflib.unified_diff([], diagnostic.splitlines(True), fromfile="/dev/null", tofile="b/backend/src/palwakf_local_agents/development_diagnostic_v1.py"))
            unified_diff = app_diff + "\n" + module_diff

            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["NO_PROXY"] = "*"
            result = subprocess.run(
                [sys.executable, str(test_script)],
                cwd=str(workspace),
                env=env,
                capture_output=True,
                text=True,
                timeout=90,
                shell=False,
            )

            source_after = {
                "backend_package": _manifest_digest(source_package),
                "frontend_dist": _manifest_digest(source_frontend_dist),
            }
            source_unchanged = source_before == source_after
            if not source_unchanged:
                raise HTTPException(status_code=409, detail="REAL_SOURCE_CHANGED_DURING_CANDIDATE_GENERATION")
            if result.returncode != 0:
                raise HTTPException(status_code=409, detail={"code": "CANDIDATE_TEST_FAILED", "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]})

            now = _utc_now()
            manifest = {
                "schema": "palwakf.local_agents.controlled_software_candidate.v1",
                "candidate_id": candidate_id,
                "candidate_key_hash": _sha256_bytes(request.candidate_key.encode("utf-8")),
                "profile_id": FIRST_CANDIDATE_PROFILE,
                "goal_id": request.goal_id,
                "goal_text": request.goal_text,
                "created_at": now,
                "updated_at": now,
                "state": "HUMAN_REVIEW_REQUIRED",
                "provider": {"provider_id": request.provider_id, "model_execution": False},
                "quality_gate": quality,
                "project_understanding": {"tool_id": TOOL_ID, "read_only": True},
                "target_files": [
                    "backend/src/palwakf_local_agents/app.py",
                    "backend/src/palwakf_local_agents/development_diagnostic_v1.py",
                ],
                "preimage": {
                    "backend/src/palwakf_local_agents/app.py": _sha256_bytes(original_app.encode("utf-8")),
                    "backend/src/palwakf_local_agents/development_diagnostic_v1.py": None,
                },
                "postimage": {
                    "backend/src/palwakf_local_agents/app.py": _sha256_bytes(candidate_app.encode("utf-8")),
                    "backend/src/palwakf_local_agents/development_diagnostic_v1.py": _sha256_bytes(diagnostic.encode("utf-8")),
                },
                "unified_diff": unified_diff,
                "tests": {
                    "runner": "DIRECT_ARGV_PYTHON",
                    "argv": ["<project-python>", "candidate_test.py"],
                    "shell": False,
                    "timeout_seconds": 90,
                    "exit_code": result.returncode,
                    "stdout": result.stdout[-6000:],
                    "stderr": result.stderr[-3000:],
                    "result": "PASS",
                },
                "source_integrity": {"before": source_before, "after": source_after, "real_source_mutation_detected": False},
                "human_review": {"decision": "PENDING", "approval_reference_stored": False},
                "source_apply": {
                    "state": "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
                    "apply_endpoint": "ABSENT_BY_DESIGN_V1",
                    "required_token_pattern": "AUTHORIZE_LOCAL_AGENTS_CANDIDATE_<CANDIDATE_ID>_CONTROLLED_APPLY",
                },
                "boundaries": {
                    "production_execution": "NOT_AUTHORIZED",
                    "real_source_write": "NONE",
                    "candidate_workspace_write": "LOCAL_ONLY",
                    "model_execution": "NONE",
                    "shell": "NONE",
                    "git": "NONE",
                    "network": "NONE",
                    "database_write": "NONE",
                    "self_apply": "BLOCKED",
                },
                "internal": {"workspace_relative": f"runtime_state/operational_core_v1/controlled_software_development_pipeline_v1/candidates/{candidate_id}/workspace"},
            }
            manifest["export"] = self._create_export(candidate_dir, manifest)
            _atomic_json(manifest_path, manifest)
            _atomic_json(self.latest_file, {"candidate_id": candidate_id, "updated_at": now})
            _append_jsonl(self.events_file, {"event_id": str(uuid.uuid4()), "occurred_at": now, "event_type": "CANDIDATE_GENERATED_AND_TESTED", "candidate_id": candidate_id, "state": manifest["state"], "real_source_mutation_detected": False})
            return {"result": "GENERATED", "idempotent_reuse": False, "candidate": self.get_candidate(candidate_id)}

    def review(self, candidate_id: str, request: ReviewRequest) -> dict[str, Any]:
        if request.human_authority_confirmed is not True:
            raise HTTPException(status_code=422, detail="HUMAN_AUTHORITY_CONFIRMATION_REQUIRED")
        with _LOCK:
            manifest = self._load_manifest(candidate_id)
            now = _utc_now()
            approval_hash = _sha256_bytes(request.human_approval_reference.encode("utf-8"))
            if request.decision == "APPROVE":
                state = "HUMAN_APPROVED_APPLY_STILL_BLOCKED"
            else:
                state = "REJECTED"
            manifest["state"] = state
            manifest["updated_at"] = now
            manifest["human_review"] = {
                "decision": request.decision,
                "reviewed_at": now,
                "approval_reference_hash": approval_hash,
                "approval_reference_stored": False,
                "note": request.note,
                "source_apply_performed": False,
            }
            _atomic_json(self._manifest_path(candidate_id), manifest)
            _append_jsonl(self.reviews_file, {"review_id": str(uuid.uuid4()), "candidate_id": candidate_id, "decision": request.decision, "reviewed_at": now, "approval_reference_hash": approval_hash, "note": request.note, "source_apply_performed": False})
            _append_jsonl(self.events_file, {"event_id": str(uuid.uuid4()), "occurred_at": now, "event_type": "CANDIDATE_HUMAN_REVIEWED", "candidate_id": candidate_id, "state": state, "source_apply_performed": False})
            return {"result": "REVIEW_RECORDED", "candidate": self.get_candidate(candidate_id)}


def create_router(project_root: Path) -> APIRouter:
    service = ControlledSoftwareDevelopmentPipelineService(project_root)
    router = APIRouter(prefix=API_PREFIX, tags=["controlled-software-development-pipeline-v1"])

    @router.get("/health")
    def health() -> dict[str, Any]: return service.health()

    @router.get("/contract")
    def contract() -> dict[str, Any]: return service.contract()

    @router.get("/providers")
    def providers() -> dict[str, Any]: return service.providers()

    @router.get("/candidates")
    def candidates(limit: int = Query(default=20, ge=1, le=50)) -> dict[str, Any]: return service.list_candidates(limit)

    @router.get("/candidates/latest")
    def latest() -> dict[str, Any]: return service.latest()

    @router.get("/candidates/{candidate_id}")
    def candidate(candidate_id: str) -> dict[str, Any]: return service.get_candidate(candidate_id)

    @router.post("/candidates/generate")
    def generate(request: GenerateCandidateRequest) -> dict[str, Any]: return service.generate(request)

    @router.post("/candidates/{candidate_id}/review")
    def review(candidate_id: str, request: ReviewRequest) -> dict[str, Any]: return service.review(candidate_id, request)

    return router


def install_controlled_software_development_pipeline_v1(app: FastAPI, *, project_root: Path) -> None:
    state = getattr(app, "state", None)
    if state is not None and getattr(state, "controlled_software_development_pipeline_v1_installed", False):
        return
    app.include_router(create_router(project_root.resolve()))
    if state is not None:
        state.controlled_software_development_pipeline_v1_installed = True
