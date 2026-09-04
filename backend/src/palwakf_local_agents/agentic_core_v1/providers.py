from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from .contracts import ProviderId


class ModelProvider(ABC):
    provider_id: str

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...

    @abstractmethod
    def generate(self, model: str, prompt: str, *, json_mode: bool = False, timeout: int = 60) -> dict[str, Any]: ...


class OllamaProvider(ModelProvider):
    provider_id = "ollama"

    def __init__(self, endpoint: str | None = None):
        self.endpoint = (endpoint or os.getenv("PALWAKF_OLLAMA_ENDPOINT") or "http://127.0.0.1:11434").rstrip("/")

    def _request(self, path: str, payload: dict[str, Any] | None = None, timeout: int = 10) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.endpoint + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_models(self) -> list[str]:
        return [m["name"] for m in self._request("/api/tags").get("models", []) if m.get("name")]

    def health(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            models = self.list_models()
            return {
                "provider_id": self.provider_id,
                "healthy": True,
                "models": models,
                "capabilities": ["generate", "structured_output", "health", "list_models"],
                "latency_ms": round((time.perf_counter()-started)*1000, 2),
                "locality": "LOCAL_ENDPOINT",
                "privacy": "LOCAL_BY_ENDPOINT_POLICY",
            }
        except Exception as error:
            return {
                "provider_id": self.provider_id,
                "healthy": False,
                "models": [],
                "error": f"{type(error).__name__}: {error}",
                "latency_ms": round((time.perf_counter()-started)*1000, 2),
            }

    def generate(self, model: str, prompt: str, *, json_mode: bool = False, timeout: int = 60) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            payload["format"] = "json"
        started = time.perf_counter()
        result = self._request("/api/generate", payload, timeout)
        return {
            "model": result.get("model", model),
            "response": result.get("response", ""),
            "latency_ms": round((time.perf_counter()-started)*1000, 2),
        }


class ExecutionProvider(ABC):
    provider_id: ProviderId
    @abstractmethod
    def health(self) -> dict[str, Any]: ...


class NativeProvider(ExecutionProvider):
    provider_id = ProviderId.NATIVE
    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id.value,
            "discovered": True,
            "healthy": True,
            "modes": ["READ_ONLY_DIAGNOSTIC"],
            "filesystem_policy": "READ_ONLY_BY_DEFAULT",
            "network_policy": "DENY_BY_DEFAULT",
            "cancel_supported": True,
            "timeout_supported": True,
        }


class HermesProvider(ExecutionProvider):
    provider_id = ProviderId.HERMES

    def __init__(self):
        self.command = os.getenv("PALWAKF_HERMES_COMMAND", "hermes")

    def health(self) -> dict[str, Any]:
        exe = shutil.which(self.command)
        if not exe:
            return {
                "provider_id": self.provider_id.value,
                "discovered": False,
                "healthy": False,
                "certification": "NOT_CERTIFIED",
                "error": "HERMES_COMMAND_NOT_DISCOVERED",
            }
        try:
            p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10, check=False)
            return {
                "provider_id": self.provider_id.value,
                "discovered": True,
                "healthy": p.returncode == 0,
                "version_output": (p.stdout or p.stderr).strip()[:500],
                "certification": "DISCOVERED_NOT_YET_READ_ONLY_CERTIFIED",
                "filesystem_policy": "DENY_UNTIL_CERTIFIED",
                "network_policy": "DENY_UNTIL_CERTIFIED",
            }
        except Exception as error:
            return {
                "provider_id": self.provider_id.value,
                "discovered": True,
                "healthy": False,
                "certification": "NOT_CERTIFIED",
                "error": f"{type(error).__name__}: {error}",
            }
