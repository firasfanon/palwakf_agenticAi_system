from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["open-source-capabilities-v1"])

MODULE_DIR = Path(__file__).resolve().parent
REGISTRY_FILE = MODULE_DIR / "open_source_capability_registry_v1.json"
ADAPTERS_FILE = MODULE_DIR / "open_source_adapter_contracts_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_registry() -> dict[str, Any]:
    return _read_json(REGISTRY_FILE)


def get_adapter_contracts() -> dict[str, Any]:
    return _read_json(ADAPTERS_FILE)


def probe_local_presence() -> dict[str, Any]:
    """Presence-only probe. It never spawns a process and never returns full paths."""
    registry = get_registry()
    results: list[dict[str, Any]] = []
    for item in registry["capabilities"]:
        detected_name: str | None = None
        for candidate in item.get("executable_candidates", []):
            resolved = shutil.which(candidate)
            if resolved:
                detected_name = Path(resolved).name
                break
        results.append(
            {
                "capability_id": item["id"],
                "present": detected_name is not None,
                "detected_executable_name": detected_name,
                "executed": False,
                "installed_by_system": False,
            }
        )
    return {
        "result": "PASS",
        "mode": "presence_only_no_execution",
        "tools": results,
        "boundaries": {
            "shell_execution": "blocked",
            "process_spawn": "blocked",
            "network": "blocked",
            "full_local_paths": "not_exposed",
        },
    }


@router.get("/api/v1/operational-core/open-source-capabilities/health")
def open_source_capabilities_health() -> dict[str, Any]:
    registry = get_registry()
    adapters = get_adapter_contracts()
    return {
        "result": "PASS",
        "mode": registry["mode"],
        "capability_count": len(registry["capabilities"]),
        "adapter_contract_count": len(adapters["contracts"]),
        "adapter_execution": "blocked",
        "download": "blocked",
        "install": "blocked",
        "network_runtime": "blocked",
    }


@router.get("/api/v1/operational-core/open-source-capabilities/registry")
def open_source_capabilities_registry() -> dict[str, Any]:
    return get_registry()


@router.get("/api/v1/operational-core/open-source-capabilities/adapters")
def open_source_capabilities_adapters() -> dict[str, Any]:
    return get_adapter_contracts()


@router.get("/api/v1/operational-core/open-source-capabilities/local-presence")
def open_source_capabilities_local_presence() -> dict[str, Any]:
    return probe_local_presence()


@router.get("/api/v1/operational-core/open-source-capabilities/boundaries")
def open_source_capabilities_boundaries() -> dict[str, Any]:
    return {
        "result": "PASS",
        "download": "blocked",
        "install": "blocked",
        "npx_pip_cargo": "blocked",
        "model_inference": "none",
        "shell_execution": "blocked",
        "git_execution": "blocked",
        "scanner_execution": "blocked",
        "network_runtime": "blocked",
        "source_mutation_by_tool": "blocked",
        "local_presence_probe": "allowed_without_process_spawn",
    }


@router.get("/agent-console/open-source-capabilities", response_class=HTMLResponse, include_in_schema=False)
def open_source_capabilities_page() -> HTMLResponse:
    project_root = Path(__file__).resolve().parents[3]
    page = project_root / "frontend" / "dist" / "open-source-capabilities" / "index.html"
    if page.is_file():
        return HTMLResponse(page.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'>"
        "<title>Open Source Capabilities</title><body>"
        "<h1>سجل القدرات مفتوحة المصدر</h1>"
        "<p>الصفحة الثابتة غير موجودة، بينما API متاح بوضع القراءة فقط.</p>"
        "</body></html>"
    )
