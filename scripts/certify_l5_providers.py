from __future__ import annotations

import ctypes
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from palwakf_local_agents.agentic_core_v1.provider_readiness import (
    HardwareProfile,
    ModelCapabilityEvidence,
    ProviderCapabilityError,
    WorkloadProfile,
    select_certified_local_route,
)
from palwakf_local_agents.agentic_core_v1.providers import OllamaProvider

OUT = ROOT / "evidence" / "l5_one_mega_batch" / "providers"
PREFERRED_MODELS = (
    "llama3.2:3b",
    "palwakf-llama3.2-3b-64k:ctx64k",
)
BROKEN_ALIAS = "palwakf-llama3.2-3b-64k:local"
STRUCTURED_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["PASS"]},
        "scope": {"type": "string", "enum": ["READ_ONLY_DIAGNOSTIC"]},
        "evidence_quality": {"type": "string", "enum": ["BOUNDED"]},
        "authority_expanded": {"type": "boolean", "const": False},
    },
    "required": [
        "status",
        "scope",
        "evidence_quality",
        "authority_expanded",
    ],
    "additionalProperties": False,
}


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _system_memory_mb() -> int:
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(_MemoryStatusEx)
    if sys.platform == "win32" and ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    ):
        return int(status.ullTotalPhys // (1024 * 1024))
    return 0


def _gpu_inventory() -> tuple[tuple[str, ...], tuple[int, ...], list[dict[str, Any]]]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return (), (), []
    if completed.returncode != 0:
        return (), (), []

    names: list[str] = []
    memory: list[int] = []
    rows: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            memory_mb = int(parts[1])
        except ValueError:
            memory_mb = 0
        names.append(parts[0])
        memory.append(memory_mb)
        rows.append(
            {"name": parts[0], "memory_mb": memory_mb, "driver": parts[2]}
        )
    return tuple(names), tuple(memory), rows


def _hardware_profile() -> tuple[HardwareProfile, list[dict[str, Any]]]:
    gpu_names, gpu_memory, gpu_rows = _gpu_inventory()
    profile = HardwareProfile(
        machine=platform.node() or "UNKNOWN_MACHINE",
        cpu=platform.processor() or platform.machine() or "UNKNOWN_CPU",
        gpu_devices=gpu_names,
        gpu_memory_mb=gpu_memory,
        system_memory_mb=_system_memory_mb(),
    )
    return profile, gpu_rows


def _representative_prompt() -> str:
    section = (
        "Repository evidence shows a governed read-only diagnostic path. "
        "Authorization is externally issued and may only be narrowed. "
        "No database, production, or cross-project mutation is allowed. "
        "A provider result must include traceable evidence and fail closed "
        "when capability is not proven. "
    )
    context = "\n".join(
        f"Evidence segment {index}: {section}" for index in range(1, 22)
    )
    return (
        "Analyze the following bounded repository evidence. "
        "Return JSON only with keys status, scope, evidence_quality, "
        "authority_expanded. status must be PASS, scope must be "
        "READ_ONLY_DIAGNOSTIC, evidence_quality must be BOUNDED, and "
        "authority_expanded must be false. Do not add prose.\n\n"
        + context
    )


def _context_length(info: dict[str, Any]) -> int:
    model_info = info.get("model_info") or {}
    for key, value in model_info.items():
        if str(key).endswith(".context_length"):
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def _semantic_pass(response: str) -> bool:
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("status") == "PASS"
        and payload.get("scope") == "READ_ONLY_DIAGNOSTIC"
        and payload.get("evidence_quality") == "BOUNDED"
        and payload.get("authority_expanded") is False
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    provider = OllamaProvider()
    hardware, gpu_rows = _hardware_profile()
    workload = WorkloadProfile(
        task_class="READ_ONLY_DIAGNOSTIC",
        workload_class="REPOSITORY_EVIDENCE_MEDIUM",
        prompt_tokens_estimate=900,
        min_context_length=8192,
        requires_structured_output=True,
        requires_tools=False,
        max_latency_ms=45_000,
        total_deadline_ms=90_000,
    )
    health = provider.health()
    version = str(health.get("version") or "")
    report: dict[str, Any] = {
        "schema": "palwakf.agentic.l5.provider_certification.v1",
        "provider": "ollama",
        "provider_version": version,
        "hardware": hardware.model_dump(mode="json"),
        "hardware_fingerprint": hardware.fingerprint,
        "gpu_inventory": gpu_rows,
        "workload": workload.model_dump(mode="json"),
        "workload_fingerprint": workload.fingerprint,
        "cloud_benchmark": "NOT_AUTHORIZED_NOT_EXECUTED",
        "broken_alias": {"model": BROKEN_ALIAS, "eligible": False},
        "attempts": [],
    }
    try:
        provider.model_info(BROKEN_ALIAS)
        report["broken_alias"]["show"] = "UNEXPECTED_PASS"
    except Exception as error:  # noqa: BLE001 -- evidence captures provider rejection
        report["broken_alias"]["show"] = "FAIL_CLOSED"
        report["broken_alias"]["error"] = f"{type(error).__name__}: {error}"

    prompt = _representative_prompt()
    evidence: list[ModelCapabilityEvidence] = []
    started = time.monotonic()

    for model in PREFERRED_MODELS:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        remaining_ms = workload.total_deadline_ms - elapsed_ms
        if remaining_ms <= 0:
            break
        attempt_timeout = max(
            1,
            min(workload.max_latency_ms, remaining_ms) // 1000,
        )
        attempt: dict[str, Any] = {"model": model}
        try:
            info = provider.model_info(model)
            capabilities = tuple(info.get("capabilities") or ())
            result = provider.generate(
                model,
                prompt,
                format_schema=STRUCTURED_SCHEMA,
                timeout=attempt_timeout,
            )
            semantic_pass = _semantic_pass(str(result.get("response") or ""))
            success = bool(semantic_pass)
            item = ModelCapabilityEvidence(
                provider_version=version,
                model=model,
                hardware_fingerprint=hardware.fingerprint,
                workload_fingerprint=workload.fingerprint,
                success=success,
                latency_ms=float(result["latency_ms"]),
                context_length=_context_length(info),
                structured_output=semantic_pass,
                tools="tools" in capabilities,
                prompt_eval_count=int(result.get("prompt_eval_count") or 0),
                prompt_tokens_per_second=float(
                    result.get("prompt_tokens_per_second") or 0
                ),
                eval_count=int(result.get("eval_count") or 0),
                tokens_per_second=float(result.get("tokens_per_second") or 0),
                failure_reason=None if success else "SEMANTIC_MISMATCH",
            )
            evidence.append(item)
            attempt.update(
                {
                    "show": "PASS",
                    "capabilities": capabilities,
                    "result": item.model_dump(mode="json"),
                    "response_excerpt": str(result.get("response") or "")[:500],
                }
            )
        except Exception as error:  # noqa: BLE001 -- certification boundary
            attempt.update(
                {
                    "show_or_inference": "FAIL_CLOSED",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            evidence.append(
                ModelCapabilityEvidence(
                    provider_version=version or "UNKNOWN",
                    model=model,
                    hardware_fingerprint=hardware.fingerprint,
                    workload_fingerprint=workload.fingerprint,
                    success=False,
                    latency_ms=float(
                        min(
                            workload.max_latency_ms,
                            int((time.monotonic() - started) * 1000),
                        )
                    ),
                    context_length=0,
                    failure_reason=f"{type(error).__name__}",
                )
            )
        report["attempts"].append(attempt)
        if evidence[-1].success:
            break

    report["capability_evidence"] = [
        item.model_dump(mode="json") for item in evidence
    ]
    try:
        decision = select_certified_local_route(
            evidence,
            hardware=hardware,
            workload=workload,
            current_provider_version=version,
            eligible_models=PREFERRED_MODELS,
        )
        report["route_decision"] = decision.model_dump(mode="json")
        report["final_result"] = "PASS"
    except ProviderCapabilityError as error:
        report["route_decision"] = {
            "status": "UNRESOLVED",
            "reason": str(error),
        }
        report["final_result"] = "FAIL_CLOSED"

    report["runtime_admission_authority"] = "NOT_GRANTED_BY_CERTIFICATION"
    report["authority_expanded"] = False
    output = OUT / "OLLAMA_L5_CERTIFICATION.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"EVIDENCE={output}")
    print(f"PROVIDER_VERSION={version}")
    print(f"HARDWARE_FINGERPRINT={hardware.fingerprint}")
    print(f"WORKLOAD_FINGERPRINT={workload.fingerprint}")
    print(f"FINAL_RESULT={report['final_result']}")
    return 0 if report["final_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
