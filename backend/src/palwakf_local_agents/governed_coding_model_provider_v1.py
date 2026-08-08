from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from palwakf_local_agents.operational_core_v1.codebase_index import CodebaseIndexer
from palwakf_local_agents import quality_accepted_tools_goal_planner_binding_v1 as planner

CONTRACT_ID = "GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1"
API_PREFIX = "/api/v1/operational-core/coding-model"
TOOL_ID = "native-code-index"
CANDIDATE_PROFILE = "MODEL_GENERATED_READ_ONLY_DIAGNOSTIC_ENDPOINT_V1"
CANDIDATE_ENDPOINT = "/api/v1/operational-core/model-generated-diagnostic/health"
MODEL_MODULE_REL = "backend/src/palwakf_local_agents/model_generated_diagnostic_v1.py"
APP_REL = "backend/src/palwakf_local_agents/app.py"
_LOCK = threading.RLock()


class ProviderSettingsInput(BaseModel):
    mode: Literal["disabled", "ollama", "openai_compatible"] = "disabled"
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = Field(default=90, ge=5, le=180)
    max_output_tokens: int = Field(default=1800, ge=256, le=4096)
    temperature: float = Field(default=0.1, ge=0.0, le=0.4)
    api_key_env_var: str = Field(default="PALWAKF_LOCAL_AGENTS_MODEL_API_KEY", min_length=3, max_length=120)


class SaveProviderSettingsRequest(BaseModel):
    settings: ProviderSettingsInput
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    confirm_no_secret_storage: bool


class ProbeProviderRequest(BaseModel):
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    confirm_loopback_only: bool


class GenerateModelCandidateRequest(BaseModel):
    candidate_key: str = Field(min_length=8, max_length=180)
    goal_id: str = Field(min_length=3, max_length=180)
    goal_text: str = Field(min_length=10, max_length=1400)
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    confirm_model_execution: bool
    confirm_candidate_workspace_only: bool
    confirm_loopback_provider_only: bool


class ModelResponse(BaseModel):
    summary: str = Field(min_length=8, max_length=1000)
    plan: list[str] = Field(min_length=1, max_length=12)
    assumptions: list[str] = Field(default_factory=list, max_length=12)
    risks: list[str] = Field(default_factory=list, max_length=12)
    module_code: str = Field(
        min_length=120,
        max_length=12000,
        description=(
            "Complete Python module containing the exact top-level functions "
            "create_router and install_model_generated_diagnostic_v1."
        ),
    )


_REQUIRED_MODEL_CODE_FUNCTIONS = frozenset({
    "create_router",
    "install_model_generated_diagnostic_v1",
})

_REQUIRED_MODEL_CODE_MARKERS = {
    "contract_id": "MODEL_GENERATED_READ_ONLY_DIAGNOSTIC_ENDPOINT_V1",
    "api_prefix": "/api/v1/operational-core/model-generated-diagnostic",
    "health_route": '"/health"',
    "source_mutation": "source_mutation",
    "none_value": "NONE",
    "local_loopback_provider": "LOCAL_LOOPBACK_PROVIDER",
    "not_authorized": "NOT_AUTHORIZED",
}

_MODEL_CODE_REFERENCE_SCAFFOLD = """from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI

CONTRACT_ID = "MODEL_GENERATED_READ_ONLY_DIAGNOSTIC_ENDPOINT_V1"
API_PREFIX = "/api/v1/operational-core/model-generated-diagnostic"


def create_router() -> APIRouter:
    router = APIRouter(prefix=API_PREFIX)

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "read_only": True,
            "source_mutation": "NONE",
            "model_execution": "LOCAL_LOOPBACK_PROVIDER",
            "shell_git_network": "BLOCKED",
            "production_execution": "NOT_AUTHORIZED",
        }

    return router


def install_model_generated_diagnostic_v1(app: FastAPI) -> None:
    target_path = API_PREFIX + "/health"
    if any(getattr(route, "path", None) == target_path for route in app.routes):
        return
    app.include_router(create_router())
"""

def _model_response_json_schema() -> dict[str, Any]:
    factory = getattr(ModelResponse, "model_json_schema", None)
    if callable(factory):
        schema = factory()
    else:
        legacy_factory = getattr(ModelResponse, "schema", None)
        if not callable(legacy_factory):
            raise RuntimeError("MODEL_RESPONSE_JSON_SCHEMA_UNAVAILABLE")
        schema = legacy_factory()
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise RuntimeError("MODEL_RESPONSE_JSON_SCHEMA_INVALID")
    return schema


_OLLAMA_GRAMMAR_SCHEMA_STRIPPED_KEYS = frozenset({
    "title",
    "description",
    "default",
    "examples",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
})


def _ollama_grammar_compatible_schema(
    schema: dict[str, Any],
) -> dict[str, Any]:
    def project(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: project(item)
                for key, item in value.items()
                if key not in _OLLAMA_GRAMMAR_SCHEMA_STRIPPED_KEYS
            }
        if isinstance(value, list):
            return [project(item) for item in value]
        return value

    projected = project(schema)
    if not isinstance(projected, dict):
        raise RuntimeError("OLLAMA_GRAMMAR_SCHEMA_INVALID")
    if projected.get("type") != "object":
        raise RuntimeError("OLLAMA_GRAMMAR_SCHEMA_ROOT_NOT_OBJECT")
    properties = projected.get("properties")
    required = projected.get("required")
    if not isinstance(properties, dict) or not properties:
        raise RuntimeError("OLLAMA_GRAMMAR_SCHEMA_PROPERTIES_INVALID")
    if not isinstance(required, list) or not required:
        raise RuntimeError("OLLAMA_GRAMMAR_SCHEMA_REQUIRED_INVALID")
    return projected


def _sanitized_provider_http_error_detail(
    exc: urllib.error.HTTPError,
) -> dict[str, Any]:
    provider_status = int(getattr(exc, "code", 0) or 0)
    provider_error_class = "PROVIDER_HTTP_ERROR"
    try:
        raw = exc.read(32_768)
    except Exception:
        raw = b""

    message = ""
    if raw:
        try:
            decoded = raw.decode("utf-8", errors="replace")
            payload = json.loads(decoded)
            if isinstance(payload, dict):
                candidate = payload.get("error")
                if isinstance(candidate, str):
                    message = candidate.lower()
        except Exception:
            message = ""

    if (
        "number of repetitions exceeds sane defaults" in message
        or "failed to parse grammar" in message
        or "failed to initialize samplers" in message
    ):
        provider_error_class = "OLLAMA_GRAMMAR_INITIALIZATION_FAILED"
    elif "model" in message and "not found" in message:
        provider_error_class = "OLLAMA_MODEL_NOT_FOUND"
    elif (
        "out of memory" in message
        or "insufficient memory" in message
        or "resource exhausted" in message
    ):
        provider_error_class = "OLLAMA_RESOURCE_EXHAUSTED"

    return {
        "code": "MODEL_PROVIDER_REQUEST_FAILED",
        "type": "HTTPError",
        "provider_status": provider_status,
        "provider_error_class": provider_error_class,
    }


def _with_model_response_schema(prompt: str, schema: dict[str, Any]) -> str:
    schema_text = json.dumps(
        schema,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        prompt.rstrip()
        + "\n\nReturn exactly one JSON object matching this JSON Schema. "
        + "Do not add markdown fences, prose, comments, or extra keys.\n"
        + schema_text
    )


def _sanitized_structured_output_issues(exc: Exception) -> list[dict[str, Any]]:
    extractor = getattr(exc, "errors", None)
    if not callable(extractor):
        return []
    try:
        raw_issues = extractor(
            include_url=False,
            include_context=False,
            include_input=False,
        )
    except TypeError:
        raw_issues = extractor()
    except Exception:
        return []

    issues: list[dict[str, Any]] = []
    if not isinstance(raw_issues, list):
        return issues
    for item in raw_issues[:12]:
        if not isinstance(item, dict):
            continue
        raw_location = item.get("loc", ())
        if not isinstance(raw_location, (list, tuple)):
            raw_location = (raw_location,)
        issues.append({
            "location": [str(part)[:80] for part in raw_location[:8]],
            "type": str(item.get("type", "validation_error"))[:120],
        })
    return issues


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


def _is_loopback_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if not _is_loopback_url(value):
        raise HTTPException(status_code=422, detail="PROVIDER_BASE_URL_MUST_BE_LOOPBACK_ONLY")
    return value


def _no_redirect_opener() -> urllib.request.OpenerDirector:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
            raise urllib.error.HTTPError(req.full_url, code, "REDIRECT_BLOCKED", headers, fp)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def _strip_json_fence(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].strip().lower() in {"```json", "```"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _approval_hash(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


class GovernedCodingModelService:
    def __init__(
        self,
        project_root: Path,
        *,
        transport: Callable[[dict[str, Any], str], str] | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.runtime_root = self.project_root / "runtime_state/operational_core_v1/governed_coding_model_provider_v1"
        self.settings_file = self.runtime_root / "provider_settings.json"
        self.runs_root = self.runtime_root / "runs"
        self.candidates_root = self.runtime_root / "candidates"
        self.events_file = self.runtime_root / "events.jsonl"
        self.latest_run_file = self.runtime_root / "latest_run.json"
        self.latest_candidate_file = self.runtime_root / "latest_candidate.json"
        self._transport_override = transport

    def contract(self) -> dict[str, Any]:
        return {
            "contract_id": CONTRACT_ID,
            "workflow": [
                "HUMAN_GOAL",
                "PROJECT_CONTEXT_READ_ONLY",
                "EXPLICIT_MODEL_AUTHORIZATION",
                "LOOPBACK_PROVIDER_CALL",
                "STRICT_STRUCTURED_OUTPUT",
                "AST_SAFETY_GATE",
                "CANDIDATE_WORKSPACE",
                "DIRECT_ARGV_TESTS",
                "UNIFIED_DIFF",
                "HUMAN_REVIEW_REQUIRED",
                "SOURCE_APPLY_BLOCKED",
            ],
            "provider_modes": ["disabled", "ollama", "openai_compatible"],
            "settings_precedence": "LOCAL_DASHBOARD_JSON_THEN_ENV_FALLBACK",
            "secret_policy": "API_KEY_VALUE_ENV_ONLY_NEVER_STORED_OR_RETURNED",
            "candidate_profile": CANDIDATE_PROFILE,
            "boundaries": {
                "production_execution": "NOT_AUTHORIZED",
                "model_execution": "EXPLICIT_HUMAN_AUTHORIZATION_ONLY",
                "provider_network": "LOOPBACK_HTTP_ONLY_NO_REDIRECTS_NO_PROXY",
                "real_source_write": "NONE",
                "candidate_workspace_write": "LOCAL_ONLY",
                "source_apply": "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
                "shell": "NONE",
                "git": "NONE",
                "database_write": "NONE",
                "self_apply": "BLOCKED",
                "human_authority": "RETAINED",
            },
        }

    def providers(self) -> dict[str, Any]:
        return {
            "providers": [
                {
                    "provider_id": "disabled",
                    "state": "SAFE_DEFAULT",
                    "model_execution": False,
                },
                {
                    "provider_id": "ollama",
                    "state": "CONTROLLED_PILOT_LOOPBACK_ONLY",
                    "protocol": "POST /api/generate",
                },
                {
                    "provider_id": "openai_compatible",
                    "state": "CONTROLLED_PILOT_LOOPBACK_ONLY",
                    "protocol": "POST /v1/chat/completions",
                },
            ],
            "external_remote_provider": "BLOCKED_BY_V1",
        }

    def _default_settings(self) -> dict[str, Any]:
        return {
            "mode": "disabled",
            "base_url": "",
            "model": "",
            "timeout_seconds": 90,
            "max_output_tokens": 1800,
            "temperature": 0.1,
            "api_key_env_var": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY",
        }

    def _load_dashboard_settings(self) -> dict[str, Any]:
        if not self.settings_file.is_file():
            return {}
        try:
            data = json.loads(self.settings_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise HTTPException(status_code=409, detail="PROVIDER_SETTINGS_CORRUPT")
        return data.get("settings", {}) if isinstance(data, dict) else {}

    def effective_settings(self) -> dict[str, Any]:
        defaults = self._default_settings()
        dashboard = self._load_dashboard_settings()
        env_map = {
            "mode": "PALWAKF_LOCAL_AGENTS_MODEL_MODE",
            "base_url": "PALWAKF_LOCAL_AGENTS_MODEL_BASE_URL",
            "model": "PALWAKF_LOCAL_AGENTS_MODEL_NAME",
            "timeout_seconds": "PALWAKF_LOCAL_AGENTS_MODEL_TIMEOUT_SECONDS",
            "max_output_tokens": "PALWAKF_LOCAL_AGENTS_MODEL_MAX_OUTPUT_TOKENS",
            "temperature": "PALWAKF_LOCAL_AGENTS_MODEL_TEMPERATURE",
            "api_key_env_var": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY_ENV_VAR",
        }
        resolved: dict[str, Any] = {}
        sources: dict[str, str] = {}
        for key, default in defaults.items():
            dashboard_value = dashboard.get(key)
            if dashboard_value not in (None, ""):
                resolved[key] = dashboard_value
                sources[key] = "dashboard_json"
                continue
            env_value = os.environ.get(env_map[key], "")
            if env_value != "":
                if key in {"timeout_seconds", "max_output_tokens"}:
                    env_value = int(env_value)
                elif key == "temperature":
                    env_value = float(env_value)
                resolved[key] = env_value
                sources[key] = "environment_fallback"
                continue
            resolved[key] = default
            sources[key] = "default"
        validated = ProviderSettingsInput(**resolved).model_dump()
        mode = validated["mode"]
        if mode != "disabled":
            validated["base_url"] = _normalize_base_url(validated["base_url"])
            if not validated["model"].strip():
                raise HTTPException(status_code=409, detail="MODEL_NAME_REQUIRED")
        public = dict(validated)
        public["api_key_configured"] = bool(os.environ.get(validated["api_key_env_var"], ""))
        public["api_key_value_stored"] = False
        public["api_key_value_returned"] = False
        public["sources"] = sources
        public["provider_scope"] = "LOOPBACK_ONLY" if mode != "disabled" else "DISABLED"
        return public

    def save_settings(self, request: SaveProviderSettingsRequest) -> dict[str, Any]:
        if request.human_authority_confirmed is not True:
            raise HTTPException(status_code=422, detail="HUMAN_AUTHORITY_CONFIRMATION_REQUIRED")
        if request.confirm_no_secret_storage is not True:
            raise HTTPException(status_code=422, detail="NO_SECRET_STORAGE_CONFIRMATION_REQUIRED")
        settings = request.settings.model_dump()
        if settings["mode"] != "disabled":
            settings["base_url"] = _normalize_base_url(settings["base_url"])
            if not settings["model"].strip():
                raise HTTPException(status_code=422, detail="MODEL_NAME_REQUIRED")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,119}", settings["api_key_env_var"]):
            raise HTTPException(status_code=422, detail="API_KEY_ENV_VAR_NAME_INVALID")
        now = _utc_now()
        record = {
            "schema": "palwakf.local_agents.governed_model_settings.v1",
            "updated_at": now,
            "settings": settings,
            "human_authority": {
                "confirmed": True,
                "approval_reference_hash": _approval_hash(request.human_approval_reference),
                "approval_reference_stored": False,
            },
            "secret_policy": {
                "api_key_value_stored": False,
                "api_key_value_source": "ENVIRONMENT_ONLY",
            },
        }
        _atomic_json(self.settings_file, record)
        _append_jsonl(self.events_file, {
            "event_id": str(uuid.uuid4()),
            "occurred_at": now,
            "event_type": "MODEL_PROVIDER_SETTINGS_UPDATED",
            "mode": settings["mode"],
            "approval_reference_hash": record["human_authority"]["approval_reference_hash"],
            "secret_value_stored": False,
        })
        return {"result": "SETTINGS_SAVED", "settings": self.effective_settings()}

    def health(self) -> dict[str, Any]:
        quality = planner.load_quality_snapshot().get("tools", {}).get(TOOL_ID, {})
        settings = self.effective_settings()
        return {
            "status": "ok",
            "contract_id": CONTRACT_ID,
            "provider_mode": settings["mode"],
            "provider_scope": settings["provider_scope"],
            "model_execution": "AVAILABLE_WITH_EXPLICIT_HUMAN_AUTHORITY" if settings["mode"] != "disabled" else "DISABLED",
            "quality_context_tool": TOOL_ID,
            "quality_state": quality.get("quality_state", "UNASSESSED"),
            "planner_state": quality.get("planner_state", "BLOCKED_UNASSESSED"),
            "real_source_write": "NONE",
            "source_apply": "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
            "shell_git": "NONE",
            "external_network": "BLOCKED",
            "loopback_network": "CONTRACT_GATED",
        }

    def _quality_gate(self) -> dict[str, Any]:
        quality = planner.load_quality_snapshot().get("tools", {}).get(TOOL_ID)
        required = {"quality_state": "QUALITY_ACCEPTED", "planner_state": "SELECTABLE", "baseline_present": True}
        observed = {key: quality.get(key) if isinstance(quality, dict) else None for key in required}
        if observed != required:
            raise HTTPException(status_code=409, detail={"code": "PROJECT_CONTEXT_QUALITY_GATE_NOT_SATISFIED", "required": required, "observed": observed})
        return {
            "tool_id": TOOL_ID,
            "quality_state": quality.get("quality_state"),
            "planner_state": quality.get("planner_state"),
            "score": quality.get("score"),
            "baseline_id": quality.get("baseline_id"),
            "suite_id": quality.get("suite_id"),
        }

    def _provider_headers(self, settings: dict[str, Any]) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if settings["mode"] == "openai_compatible":
            key = os.environ.get(settings["api_key_env_var"], "")
            if key:
                headers["Authorization"] = "Bearer " + key
        return headers

    def _http_json(self, method: str, url: str, settings: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not _is_loopback_url(url):
            raise HTTPException(status_code=422, detail="MODEL_REQUEST_MUST_REMAIN_LOOPBACK_ONLY")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url=url, data=body, method=method, headers=self._provider_headers(settings))
        opener = _no_redirect_opener()
        try:
            with opener.open(request, timeout=settings["timeout_seconds"]) as response:
                raw = response.read(2_500_000)
                if response.status < 200 or response.status >= 300:
                    raise HTTPException(status_code=502, detail="MODEL_PROVIDER_HTTP_STATUS_INVALID")
        except HTTPException:
            raise
        except urllib.error.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=_sanitized_provider_http_error_detail(exc),
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "MODEL_PROVIDER_REQUEST_FAILED",
                    "type": type(exc).__name__,
                },
            ) from None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(status_code=502, detail="MODEL_PROVIDER_RESPONSE_NOT_JSON")
        if not isinstance(value, dict):
            raise HTTPException(status_code=502, detail="MODEL_PROVIDER_RESPONSE_NOT_OBJECT")
        return value

    def probe(self, request: ProbeProviderRequest) -> dict[str, Any]:
        if request.human_authority_confirmed is not True:
            raise HTTPException(status_code=422, detail="HUMAN_AUTHORITY_CONFIRMATION_REQUIRED")
        if request.confirm_loopback_only is not True:
            raise HTTPException(status_code=422, detail="LOOPBACK_ONLY_CONFIRMATION_REQUIRED")
        settings = self.effective_settings()
        if settings["mode"] == "disabled":
            raise HTTPException(status_code=409, detail="MODEL_PROVIDER_DISABLED")
        if settings["mode"] == "ollama":
            url = settings["base_url"] + "/api/tags"
        else:
            url = settings["base_url"] + "/v1/models"
        if self._transport_override is not None:
            raw = self._transport_override(settings, "PROBE")
            payload = json.loads(raw)
        else:
            payload = self._http_json("GET", url, settings)
        now = _utc_now()
        _append_jsonl(self.events_file, {
            "event_id": str(uuid.uuid4()),
            "occurred_at": now,
            "event_type": "MODEL_PROVIDER_PROBED",
            "mode": settings["mode"],
            "approval_reference_hash": _approval_hash(request.human_approval_reference),
            "approval_reference_stored": False,
            "loopback_only": True,
        })
        return {
            "result": "PROBE_PASS",
            "provider_mode": settings["mode"],
            "loopback_only": True,
            "response_keys": sorted(payload.keys())[:20],
            "secret_value_returned": False,
        }

    def _project_context(self) -> dict[str, Any]:
        index = CodebaseIndexer(self.project_root).build(detail_limit=80)
        summary = index.get("summary", {}) if isinstance(index, dict) else {}
        return {
            "summary": summary,
            "allowed_read_roots": ["frontend/src", "backend/src/palwakf_local_agents", "agents", "docs"],
            "source_contents_in_prompt": False,
            "context_tool": TOOL_ID,
        }

    def _prompt(self, request: GenerateModelCandidateRequest, context: dict[str, Any]) -> str:
        schema = {
            "summary": "string",
            "plan": ["string"],
            "assumptions": ["string"],
            "risks": ["string"],
            "module_code": "string",
        }
        return (
            "You are generating one strictly read-only FastAPI diagnostic module for a governed local candidate workspace.\n"
            "Return JSON only, no markdown. Required schema: " + json.dumps(schema) + "\n"
            "The module_code value must be a complete Python module, not pseudocode and not a code fence.\n"
            "It MUST contain both exact TOP-LEVEL function definitions:\n"
            "1. def create_router() -> APIRouter:\n"
            "2. def install_model_generated_diagnostic_v1(app: FastAPI) -> None:\n"
            "Do not rename, nest, alias, wrap in a class, replace, or omit either function.\n"
            "Use the following safe reference scaffold as the module_code implementation; contract values and function names must not change:\n"
            + _MODEL_CODE_REFERENCE_SCAFFOLD
            + "\nEnd of required reference scaffold.\n"
            "Additional restrictions:\n"
            "- import only from __future__, typing, and fastapi\n"
            "- not read files, write files, access databases, open sockets, launch processes, execute code dynamically, or call external services\n"
            "Goal ID: " + request.goal_id + "\n"
            "Goal: " + request.goal_text + "\n"
            "Project context (metadata only): " + json.dumps(context, ensure_ascii=False, separators=(",", ":"))[:8000]
        )

    def _call_provider(self, settings: dict[str, Any], prompt: str) -> tuple[str, dict[str, Any]]:
        if self._transport_override is not None:
            return self._transport_override(settings, prompt), {"transport": "SELFTEST_OVERRIDE", "loopback": True}
        schema = _model_response_json_schema()
        structured_prompt = _with_model_response_schema(prompt, schema)
        if settings["mode"] == "ollama":
            grammar_schema = _ollama_grammar_compatible_schema(schema)
            url = settings["base_url"] + "/api/generate"
            payload = {
                "model": settings["model"],
                "prompt": structured_prompt,
                "stream": False,
                "think": False,
                "format": grammar_schema,
                "options": {
                    "temperature": settings["temperature"],
                    "num_predict": settings["max_output_tokens"],
                },
            }
            response = self._http_json("POST", url, settings, payload)
            text = response.get("response")
        elif settings["mode"] == "openai_compatible":
            url = settings["base_url"] + "/v1/chat/completions"
            payload = {
                "model": settings["model"],
                "messages": [
                    {"role": "system", "content": "Return strict JSON only for the governed coding candidate schema."},
                    {"role": "user", "content": structured_prompt},
                ],
                "temperature": settings["temperature"],
                "max_tokens": settings["max_output_tokens"],
                "response_format": {"type": "json_object"},
            }
            response = self._http_json("POST", url, settings, payload)
            try:
                text = response["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                text = None
        else:
            raise HTTPException(status_code=409, detail="MODEL_PROVIDER_DISABLED")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=502, detail="MODEL_PROVIDER_TEXT_MISSING")
        return text, {
            "transport": settings["mode"],
            "loopback": True,
            "structured_output_schema": (
                "OLLAMA_GRAMMAR_COMPATIBLE_STRUCTURAL_V1"
                if settings["mode"] == "ollama"
                else "FULL_SCHEMA_PROMPT_WITH_PROVIDER_JSON_MODE"
            ),
            "full_pydantic_validation": True,
        }

    def _validate_model_code(self, code: str) -> dict[str, Any]:
        try:
            tree = ast.parse(code)
            compile(code, "model_generated_diagnostic_v1.py", "exec")
        except SyntaxError as exc:
            raise HTTPException(status_code=422, detail={"code": "MODEL_CODE_SYNTAX_INVALID", "line": exc.lineno})
        allowed_imports = {"__future__", "typing", "fastapi"}
        forbidden_calls = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}
        functions: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in allowed_imports:
                        raise HTTPException(status_code=422, detail="MODEL_CODE_IMPORT_NOT_ALLOWED=" + alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module not in allowed_imports:
                    raise HTTPException(status_code=422, detail="MODEL_CODE_IMPORT_NOT_ALLOWED=" + str(node.module))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.add(node.name)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                raise HTTPException(status_code=422, detail="MODEL_CODE_CALL_NOT_ALLOWED=" + node.func.id)
            elif isinstance(node, ast.Name) and node.id in {"os", "sys", "subprocess", "socket", "requests", "urllib", "pathlib", "shutil"}:
                raise HTTPException(status_code=422, detail="MODEL_CODE_NAME_NOT_ALLOWED=" + node.id)
        missing_functions = sorted(_REQUIRED_MODEL_CODE_FUNCTIONS - functions)
        if missing_functions:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "MODEL_CODE_REQUIRED_FUNCTIONS_MISSING",
                    "type": "ContractValidationError",
                    "missing_functions": missing_functions,
                    "required_function_count": len(_REQUIRED_MODEL_CODE_FUNCTIONS),
                    "present_required_function_count": (
                        len(_REQUIRED_MODEL_CODE_FUNCTIONS) - len(missing_functions)
                    ),
                },
            )
        missing_markers = sorted(
            marker_id
            for marker_id, marker in _REQUIRED_MODEL_CODE_MARKERS.items()
            if marker not in code
        )
        if missing_markers:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "MODEL_CODE_REQUIRED_CONTRACT_MARKERS_MISSING",
                    "type": "ContractValidationError",
                    "missing_marker_ids": missing_markers,
                },
            )
        return {"ast_parse": "PASS", "compile": "PASS", "import_allowlist": "PASS", "forbidden_calls": "PASS"}

    def _patch_app(self, text: str) -> str:
        import_line = "from palwakf_local_agents.model_generated_diagnostic_v1 import install_model_generated_diagnostic_v1"
        call_line = "install_model_generated_diagnostic_v1(app)"
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
                raise RuntimeError("MODEL_CANDIDATE_RESOLVED_PROJECT_ROOT_NOT_EXACTLY_ONCE")
            index = matches[0]
            indent = lines[index][: len(lines[index]) - len(lines[index].lstrip())]
            lines.insert(index + 1, indent + call_line + "\n")
            text = "".join(lines)
        if text.count(import_line) != 1 or text.count(call_line) != 1:
            raise RuntimeError("MODEL_CANDIDATE_APP_PATCH_NOT_IDEMPOTENT")
        compile(text, "candidate-app.py", "exec")
        return text

    def _write_candidate_file(self, workspace: Path, relative: str, content: str) -> Path:
        rel = _safe_relative(relative)
        allowed = {
            PurePosixPath(APP_REL),
            PurePosixPath(MODEL_MODULE_REL),
            PurePosixPath("candidate_test.py"),
        }
        if rel not in allowed:
            raise RuntimeError("MODEL_CANDIDATE_EDITOR_TARGET_NOT_ALLOWED=" + rel.as_posix())
        target = workspace.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return target

    def _candidate_test_script(self) -> str:
        return '''from __future__ import annotations\nimport asyncio, json, os, sys\nfrom pathlib import Path\nroot=Path(__file__).resolve().parent\nsys.path.insert(0,str(root/"backend/src"))\nos.environ["PALWAKF_LOCAL_AGENTS_SOURCE_ROOT"]=str(root)\nfrom palwakf_local_agents.app import app\npath="/api/v1/operational-core/model-generated-diagnostic/health"\nopenapi=app.openapi().get("paths",{})\nassert "get" in openapi.get(path,{}),openapi.get(path)\nasync def request():\n messages=[]; consumed=False\n async def receive():\n  nonlocal consumed\n  if not consumed:\n   consumed=True; return {"type":"http.request","body":b"","more_body":False}\n  return {"type":"http.disconnect"}\n async def send(message): messages.append(message)\n scope={"type":"http","asgi":{"version":"3.0","spec_version":"2.3"},"http_version":"1.1","method":"GET","scheme":"http","path":path,"raw_path":path.encode(),"query_string":b"","root_path":"","headers":[(b"host",b"candidate-test")],"client":("127.0.0.1",58002),"server":("candidate-test",80),"state":{}}\n await app(scope,receive,send)\n status=None; body=[]\n for message in messages:\n  if message["type"]=="http.response.start": status=int(message["status"])\n  elif message["type"]=="http.response.body": body.append(message.get("body",b""))\n assert status==200,status\n payload=json.loads(b"".join(body).decode())\n assert payload["read_only"] is True\n assert payload["source_mutation"]=="NONE"\n assert payload["model_execution"]=="LOCAL_LOOPBACK_PROVIDER"\n return payload\npayload=asyncio.run(request())\nprint("MODEL_CANDIDATE_APP_IMPORT=PASS")\nprint("MODEL_CANDIDATE_OPENAPI=PASS")\nprint("MODEL_CANDIDATE_HTTP=200")\nprint("MODEL_CANDIDATE_BOUNDARIES=PASS")\nprint(json.dumps(payload,sort_keys=True))\n'''

    def _create_export(self, candidate_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        export_path = candidate_dir / "candidate_export.zip"
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as archive:
            public = {key: value for key, value in manifest.items() if key != "internal"}
            archive.writestr("candidate_manifest.json", json.dumps(public, ensure_ascii=False, indent=2))
            archive.writestr("candidate.patch", manifest["unified_diff"])
            for rel in manifest["target_files"]:
                path = candidate_dir / "workspace" / rel
                if path.is_file():
                    archive.write(path, arcname="workspace/" + rel)
        return {"filename": export_path.name, "size_bytes": export_path.stat().st_size, "sha256": _sha256_file(export_path)}

    def _candidate_id(self, candidate_key: str) -> str:
        return "model-cand-" + _sha256_bytes(candidate_key.encode("utf-8"))[:16].lower()

    def _run_id(self) -> str:
        return "model-run-" + uuid.uuid4().hex[:16]

    def _candidate_manifest_path(self, candidate_id: str) -> Path:
        return self.candidates_root / candidate_id / "candidate_manifest.json"

    def _load_candidate(self, candidate_id: str) -> dict[str, Any]:
        path = self._candidate_manifest_path(candidate_id)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="MODEL_CANDIDATE_NOT_FOUND")
        return json.loads(path.read_text(encoding="utf-8"))

    def _public_candidate(self, record: dict[str, Any], include_diff: bool = True) -> dict[str, Any]:
        public = {key: value for key, value in record.items() if key != "internal"}
        if not include_diff:
            public.pop("unified_diff", None)
        return public

    def list_candidates(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        records: list[dict[str, Any]] = []
        if self.candidates_root.is_dir():
            for path in sorted(self.candidates_root.glob("*/candidate_manifest.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:limit]:
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                records.append(self._public_candidate(record, include_diff=False))
        return {"candidates": records, "count": len(records), "limit": limit}

    def latest_candidate(self) -> dict[str, Any]:
        if not self.latest_candidate_file.is_file():
            return {"available": False, "message": "NO_MODEL_CANDIDATE_GENERATED"}
        candidate_id = json.loads(self.latest_candidate_file.read_text(encoding="utf-8")).get("candidate_id")
        if not candidate_id:
            return {"available": False, "message": "NO_MODEL_CANDIDATE_GENERATED"}
        return {"available": True, "candidate": self._public_candidate(self._load_candidate(candidate_id))}

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._public_candidate(self._load_candidate(candidate_id))

    def generate(self, request: GenerateModelCandidateRequest) -> dict[str, Any]:
        if request.human_authority_confirmed is not True:
            raise HTTPException(status_code=422, detail="HUMAN_AUTHORITY_CONFIRMATION_REQUIRED")
        if request.confirm_model_execution is not True:
            raise HTTPException(status_code=422, detail="MODEL_EXECUTION_CONFIRMATION_REQUIRED")
        if request.confirm_candidate_workspace_only is not True:
            raise HTTPException(status_code=422, detail="CANDIDATE_WORKSPACE_CONFIRMATION_REQUIRED")
        if request.confirm_loopback_provider_only is not True:
            raise HTTPException(status_code=422, detail="LOOPBACK_ONLY_CONFIRMATION_REQUIRED")
        settings = self.effective_settings()
        if settings["mode"] == "disabled":
            raise HTTPException(status_code=409, detail="MODEL_PROVIDER_DISABLED")
        quality = self._quality_gate()
        candidate_id = self._candidate_id(request.candidate_key)
        candidate_dir = self.candidates_root / candidate_id
        manifest_path = self._candidate_manifest_path(candidate_id)

        with _LOCK:
            if manifest_path.is_file():
                return {"result": "ALREADY_GENERATED", "idempotent_reuse": True, "candidate": self._public_candidate(self._load_candidate(candidate_id))}

            source_package = self.project_root / "backend/src/palwakf_local_agents"
            source_frontend_dist = self.project_root / "frontend/dist"
            source_app = self.project_root / APP_REL
            if not source_app.is_file():
                raise HTTPException(status_code=409, detail="SOURCE_APP_NOT_FOUND")
            source_before = {
                "backend_package": _manifest_digest(source_package),
                "frontend_dist": _manifest_digest(source_frontend_dist),
            }
            context = self._project_context()
            prompt = self._prompt(request, context)
            run_id = self._run_id()
            run_dir = self.runs_root / run_id
            started_at = _utc_now()
            approval_hash = _approval_hash(request.human_approval_reference)
            raw_text, transport = self._call_provider(settings, prompt)
            try:
                parsed = json.loads(_strip_json_fence(raw_text))
                validator = getattr(ModelResponse, "model_validate", None)
                model_response = (
                    validator(parsed)
                    if callable(validator)
                    else ModelResponse(**parsed)
                )
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "MODEL_STRUCTURED_OUTPUT_INVALID",
                        "type": type(exc).__name__,
                        "stage": "JSON_DECODE",
                        "issues": [],
                    },
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "MODEL_STRUCTURED_OUTPUT_INVALID",
                        "type": type(exc).__name__,
                        "stage": "SCHEMA_VALIDATION",
                        "issues": _sanitized_structured_output_issues(exc),
                    },
                )
            safety = self._validate_model_code(model_response.module_code)

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
            self._write_candidate_file(workspace, APP_REL, candidate_app)
            self._write_candidate_file(workspace, MODEL_MODULE_REL, model_response.module_code)
            test_script = self._write_candidate_file(workspace, "candidate_test.py", self._candidate_test_script())

            app_diff = "".join(difflib.unified_diff(original_app.splitlines(True), candidate_app.splitlines(True), fromfile="a/" + APP_REL, tofile="b/" + APP_REL))
            module_diff = "".join(difflib.unified_diff([], model_response.module_code.splitlines(True), fromfile="/dev/null", tofile="b/" + MODEL_MODULE_REL))
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
            if source_before != source_after:
                raise HTTPException(status_code=409, detail="REAL_SOURCE_CHANGED_DURING_MODEL_CANDIDATE_GENERATION")
            if result.returncode != 0:
                raise HTTPException(status_code=409, detail={"code": "MODEL_CANDIDATE_TEST_FAILED", "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]})

            completed_at = _utc_now()
            run_record = {
                "schema": "palwakf.local_agents.governed_model_run.v1",
                "run_id": run_id,
                "candidate_id": candidate_id,
                "started_at": started_at,
                "completed_at": completed_at,
                "provider": {
                    "mode": settings["mode"],
                    "model": settings["model"],
                    "base_url_scope": "LOOPBACK_ONLY",
                    "transport": transport["transport"],
                    "api_key_value_stored": False,
                },
                "human_authority": {
                    "confirmed": True,
                    "approval_reference_hash": approval_hash,
                    "approval_reference_stored": False,
                },
                "prompt": {
                    "sha256": _sha256_bytes(prompt.encode("utf-8")),
                    "plaintext_stored": False,
                    "source_contents_included": False,
                },
                "response": {
                    "sha256": _sha256_bytes(raw_text.encode("utf-8")),
                    "raw_plaintext_stored": False,
                    "structured_output_valid": True,
                },
                "result": "PASS",
                "boundaries": {
                    "real_source_write": "NONE",
                    "candidate_workspace_write": "LOCAL_ONLY",
                    "external_network": "NONE",
                    "loopback_network": "MODEL_PROVIDER_ONLY",
                    "shell": "NONE",
                    "git": "NONE",
                    "database_write": "NONE",
                    "source_apply": "BLOCKED",
                },
            }
            manifest = {
                "schema": "palwakf.local_agents.model_generated_candidate.v1",
                "candidate_id": candidate_id,
                "candidate_key_hash": _sha256_bytes(request.candidate_key.encode("utf-8")),
                "profile_id": CANDIDATE_PROFILE,
                "parent_pipeline_contract": "CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_V1",
                "goal_id": request.goal_id,
                "goal_text": request.goal_text,
                "created_at": completed_at,
                "updated_at": completed_at,
                "state": "MODEL_CANDIDATE_HUMAN_REVIEW_REQUIRED",
                "provider": {
                    "mode": settings["mode"],
                    "model": settings["model"],
                    "execution": "LOCAL_LOOPBACK_PROVIDER",
                    "admission_state": "CONTROLLED_PILOT_HUMAN_AUTHORIZED",
                },
                "model_output": {
                    "summary": model_response.summary,
                    "plan": model_response.plan,
                    "assumptions": model_response.assumptions,
                    "risks": model_response.risks,
                    "module_code_sha256": _sha256_bytes(model_response.module_code.encode("utf-8")),
                    "raw_response_stored": False,
                },
                "quality_gate": quality,
                "project_context": context,
                "safety_gate": safety,
                "target_files": [APP_REL, MODEL_MODULE_REL],
                "preimage": {
                    APP_REL: _sha256_bytes(original_app.encode("utf-8")),
                    MODEL_MODULE_REL: None,
                },
                "postimage": {
                    APP_REL: _sha256_bytes(candidate_app.encode("utf-8")),
                    MODEL_MODULE_REL: _sha256_bytes(model_response.module_code.encode("utf-8")),
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
                "source_integrity": {
                    "before": source_before,
                    "after": source_after,
                    "real_source_mutation_detected": False,
                },
                "human_review": {
                    "decision": "PENDING",
                    "approval_reference_stored": False,
                },
                "source_apply": {
                    "state": "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
                    "apply_endpoint": "ABSENT_BY_DESIGN_V1",
                    "required_token_pattern": "AUTHORIZE_LOCAL_AGENTS_CANDIDATE_<CANDIDATE_ID>_CONTROLLED_APPLY",
                },
                "boundaries": run_record["boundaries"],
                "run_id": run_id,
                "internal": {
                    "workspace_relative": f"runtime_state/operational_core_v1/governed_coding_model_provider_v1/candidates/{candidate_id}/workspace",
                },
            }
            manifest["export"] = self._create_export(candidate_dir, manifest)
            _atomic_json(manifest_path, manifest)
            _atomic_json(run_dir / "run.json", run_record)
            _atomic_json(self.latest_candidate_file, {"candidate_id": candidate_id, "updated_at": completed_at})
            _atomic_json(self.latest_run_file, {"run_id": run_id, "updated_at": completed_at})
            _append_jsonl(self.events_file, {
                "event_id": str(uuid.uuid4()),
                "occurred_at": completed_at,
                "event_type": "MODEL_CANDIDATE_GENERATED_AND_TESTED",
                "candidate_id": candidate_id,
                "run_id": run_id,
                "state": manifest["state"],
                "real_source_mutation_detected": False,
                "source_apply_performed": False,
            })
            return {"result": "GENERATED", "idempotent_reuse": False, "candidate": self._public_candidate(manifest), "run": run_record}

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        records: list[dict[str, Any]] = []
        if self.runs_root.is_dir():
            for path in sorted(self.runs_root.glob("*/run.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:limit]:
                try:
                    records.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return {"runs": records, "count": len(records), "limit": limit}

    def latest_run(self) -> dict[str, Any]:
        if not self.latest_run_file.is_file():
            return {"available": False, "message": "NO_MODEL_RUN_EXECUTED"}
        run_id = json.loads(self.latest_run_file.read_text(encoding="utf-8")).get("run_id")
        path = self.runs_root / str(run_id) / "run.json"
        if not path.is_file():
            return {"available": False, "message": "NO_MODEL_RUN_EXECUTED"}
        return {"available": True, "run": json.loads(path.read_text(encoding="utf-8"))}


def create_router(project_root: Path) -> APIRouter:
    service = GovernedCodingModelService(project_root)
    router = APIRouter(prefix=API_PREFIX, tags=["governed-coding-model-provider-v1"])

    @router.get("/health")
    def health() -> dict[str, Any]: return service.health()

    @router.get("/contract")
    def contract() -> dict[str, Any]: return service.contract()

    @router.get("/providers")
    def providers() -> dict[str, Any]: return service.providers()

    @router.get("/settings")
    def settings() -> dict[str, Any]: return service.effective_settings()

    @router.post("/settings")
    def save_settings(request: SaveProviderSettingsRequest) -> dict[str, Any]: return service.save_settings(request)

    @router.post("/providers/probe")
    def probe(request: ProbeProviderRequest) -> dict[str, Any]: return service.probe(request)

    @router.get("/runs")
    def runs(limit: int = Query(default=20, ge=1, le=50)) -> dict[str, Any]: return service.list_runs(limit)

    @router.get("/runs/latest")
    def latest_run() -> dict[str, Any]: return service.latest_run()

    @router.get("/candidates")
    def candidates(limit: int = Query(default=20, ge=1, le=50)) -> dict[str, Any]: return service.list_candidates(limit)

    @router.get("/candidates/latest")
    def latest_candidate() -> dict[str, Any]: return service.latest_candidate()

    @router.get("/candidates/{candidate_id}")
    def candidate(candidate_id: str) -> dict[str, Any]: return service.get_candidate(candidate_id)

    @router.post("/candidates/generate")
    def generate(request: GenerateModelCandidateRequest) -> dict[str, Any]: return service.generate(request)

    return router


def install_governed_coding_model_provider_v1(app: FastAPI, *, project_root: Path) -> None:
    state = getattr(app, "state", None)
    if state is not None and getattr(state, "governed_coding_model_provider_v1_installed", False):
        return
    app.include_router(create_router(project_root.resolve()))
    if state is not None:
        state.governed_coding_model_provider_v1_installed = True
