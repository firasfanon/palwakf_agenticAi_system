from __future__ import annotations

import json
import os
import platform
import shutil
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_ollama_url() -> str:
    configured = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"
    if "://" not in configured:
        configured = "http://" + configured
    parsed = urllib.parse.urlparse(configured)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return "http://127.0.0.1:11434"
    port = parsed.port or 11434
    return f"http://{parsed.hostname}:{port}"


def inspect_local_model_readiness(probe: bool = False) -> dict[str, Any]:
    endpoint = _safe_ollama_url()
    models: list[dict[str, Any]] = []
    reachable: bool | None = None
    probe_error: str | None = None
    if probe:
        try:
            req = urllib.request.Request(endpoint + "/api/tags", method="GET", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1.8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                reachable = True
                for item in payload.get("models", [])[:50]:
                    models.append({
                        "name": item.get("name") or item.get("model"),
                        "size": item.get("size"),
                        "modified_at": item.get("modified_at"),
                    })
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            reachable = False
            probe_error = type(exc).__name__
    readiness = "READY_FOR_PROMPT_ONLY_GATE" if reachable and models else ("OLLAMA_REACHABLE_NO_MODELS" if reachable else "NOT_PROBED" if not probe else "NOT_READY")
    return {
        "schema": "palwakf.local_agents.local_model_readiness.v1",
        "checked_at": _now(),
        "probe_requested": probe,
        "ollama_binary_detected": bool(shutil.which("ollama")),
        "ollama_endpoint": endpoint,
        "ollama_reachable": reachable,
        "models": models,
        "model_count": len(models),
        "readiness": readiness,
        "probe_error": probe_error,
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "gates": {
            "model_execution": "blocked",
            "tool_access_from_model": "blocked",
            "pilot_execution": "not_authorized",
            "next_allowed_stage": "prompt_only_controlled_pilot_after_separate_authorization",
        },
        "no_model_invocation": True,
    }
