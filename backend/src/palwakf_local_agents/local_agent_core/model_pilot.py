from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException


CONFIG_RELATIVE_PATH = Path("config") / "local_agent_model_pilot_v1.json"
ALLOWED_BASE_URLS = {"http://127.0.0.1:11434", "http://localhost:11434"}
ALLOWED_WORKSPACE_ID = "palwakf_government"
ALLOWED_AGENT_ID = "task_planning_runbook_agent_v1"


@dataclass(frozen=True)
class ModelPilotConfig:
    enabled: bool
    workspace_id: str
    agent_id: str
    provider: str
    base_url: str
    model: str
    timeout_seconds: int
    max_output_chars: int
    max_predict_tokens: int
    temperature: float
    human_review_required: bool
    external_network: str


def _error(status: int, code: str, **extra: Any) -> None:
    raise HTTPException(status_code=status, detail={"code": code, **extra})


def _validate_base_url(value: str) -> str:
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if normalized not in ALLOWED_BASE_URLS:
        raise ValueError("MODEL_PILOT_BASE_URL_NOT_LOCAL_ALLOWED")
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 11434:
        raise ValueError("MODEL_PILOT_BASE_URL_NOT_LOCAL_ALLOWED")
    if parsed.path not in {"", "/"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("MODEL_PILOT_BASE_URL_NOT_LOCAL_ALLOWED")
    return normalized


def _default_config() -> dict[str, Any]:
    return {
        "schema_version": "LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1",
        "enabled": False,
        "workspace_id": ALLOWED_WORKSPACE_ID,
        "agent_id": ALLOWED_AGENT_ID,
        "provider": "ollama_local_only",
        "base_url": "http://127.0.0.1:11434",
        "model": "qwen2.5:3b",
        "timeout_seconds": 45,
        "max_output_chars": 6000,
        "max_predict_tokens": 700,
        "temperature": 0.1,
        "human_review_required": True,
        "external_network": "NONE",
    }


def load_model_pilot_config(project_root: Path) -> ModelPilotConfig:
    path = project_root / CONFIG_RELATIVE_PATH
    data = _default_config()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("MODEL_PILOT_CONFIG_INVALID_JSON") from error
        if not isinstance(loaded, dict):
            raise ValueError("MODEL_PILOT_CONFIG_OBJECT_REQUIRED")
        data.update(loaded)
    if data.get("schema_version") != "LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1":
        raise ValueError("MODEL_PILOT_CONFIG_SCHEMA_INVALID")
    if data.get("workspace_id") != ALLOWED_WORKSPACE_ID or data.get("agent_id") != ALLOWED_AGENT_ID:
        raise ValueError("MODEL_PILOT_SCOPE_CONFIG_INVALID")
    if data.get("provider") != "ollama_local_only":
        raise ValueError("MODEL_PILOT_PROVIDER_NOT_ALLOWED")
    base_url = _validate_base_url(str(data.get("base_url", "")))
    model = str(data.get("model", "")).strip()
    if not model or len(model) > 128:
        raise ValueError("MODEL_PILOT_MODEL_INVALID")
    timeout_seconds = int(data.get("timeout_seconds", 0))
    max_output_chars = int(data.get("max_output_chars", 0))
    max_predict_tokens = int(data.get("max_predict_tokens", 0))
    temperature = float(data.get("temperature", 0))
    if not 5 <= timeout_seconds <= 120 or not 500 <= max_output_chars <= 12000 or not 64 <= max_predict_tokens <= 1200 or not 0 <= temperature <= 0.3:
        raise ValueError("MODEL_PILOT_BOUNDS_INVALID")
    if data.get("external_network") != "NONE" or data.get("human_review_required") is not True:
        raise ValueError("MODEL_PILOT_SECURITY_CONTRACT_INVALID")
    return ModelPilotConfig(
        enabled=bool(data.get("enabled")),
        workspace_id=ALLOWED_WORKSPACE_ID,
        agent_id=ALLOWED_AGENT_ID,
        provider="ollama_local_only",
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_output_chars=max_output_chars,
        max_predict_tokens=max_predict_tokens,
        temperature=temperature,
        human_review_required=True,
        external_network="NONE",
    )


def pilot_status(project_root: Path) -> dict[str, Any]:
    config = load_model_pilot_config(project_root)
    return {
        "pilot_contract": "LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1",
        "pilot_enabled": config.enabled,
        "workspace_id": config.workspace_id,
        "agent_id": config.agent_id,
        "provider": config.provider,
        "model": config.model,
        "model_endpoint_scope": "LOOPBACK_ONLY_127_0_0_1_OR_LOCALHOST_PORT_11434",
        "external_network": "NONE",
        "tool_execution": "NONE",
        "shell_execution": "NONE",
        "git_write": "NONE",
        "database_write": "NONE",
        "deployment": "NONE",
        "cross_workspace_access": "DENY",
        "memory_write": "NONE",
        "human_review": "MANDATORY",
        "activation_state": "DISABLED_BY_DEFAULT" if not config.enabled else "EXPLICITLY_ENABLED_REQUIRES_SEPARATE_RUNTIME_AUTHORIZATION",
    }


def _prompt(objective: str, source_summary: str, evidence_references: list[str]) -> str:
    evidence = "\n".join(f"- {item}" for item in evidence_references) or "- لا توجد مراجع أدلة مرفقة"
    return (
        "أنت مساعد محلي محكوم لإعداد مسودة خطة تشغيل فقط. \n"
        "المطلوب: أعِد مسودة عربية منظمة تشمل الهدف، النطاق، خطوات التحقق، بوابات القبول، مخاطر، وخطوة مراجعة بشرية. \n"
        "محظور: تنفيذ أوامر، اقتراح تنفيذ تلقائي، استعمال أدوات، كتابة ملفات، تعديل مستودع، نشر، أو التعامل مع الشبكة. \n"
        "يجب أن تذكر صراحة أن المخرج مسودة للمراجعة البشرية ولا يمنح تفويض تنفيذ.\n\n"
        f"الهدف:\n{objective}\n\n"
        f"الملخص المصدر:\n{source_summary}\n\n"
        f"مراجع الأدلة:\n{evidence}\n"
    )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise HTTPError(req.full_url, code, "MODEL_PILOT_REDIRECT_DENIED", headers, fp)


def generate_local_draft(config: ModelPilotConfig, objective: str, source_summary: str, evidence_references: list[str]) -> dict[str, Any]:
    if not config.enabled:
        _error(403, "MODEL_PILOT_DISABLED")
    request_payload = {
        "model": config.model,
        "prompt": _prompt(objective, source_summary, evidence_references),
        "stream": False,
        "options": {"temperature": config.temperature, "num_predict": config.max_predict_tokens},
    }
    encoded = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{config.base_url}/api/generate",
        data=encoded,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with build_opener(_NoRedirect()).open(request, timeout=config.timeout_seconds) as response:
            if response.status != 200:
                _error(502, "MODEL_PILOT_LOCAL_PROVIDER_HTTP_ERROR", provider_status=response.status)
            raw = response.read().decode("utf-8")
    except HTTPException:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        _error(503, "MODEL_PILOT_LOCAL_PROVIDER_UNAVAILABLE", error_type=type(error).__name__)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        _error(502, "MODEL_PILOT_LOCAL_PROVIDER_INVALID_JSON", error_type=type(error).__name__)
    text = str(data.get("response", "")).strip()
    if not text:
        _error(502, "MODEL_PILOT_LOCAL_PROVIDER_EMPTY_OUTPUT")
    return {
        "draft_text": text[:config.max_output_chars],
        "provider": config.provider,
        "model": config.model,
        "endpoint_scope": "LOOPBACK_ONLY",
        "tool_execution": "NONE",
        "external_network": "NONE",
    }
