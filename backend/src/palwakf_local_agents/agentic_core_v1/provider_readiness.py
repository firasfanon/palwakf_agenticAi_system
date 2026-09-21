from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderCapabilityError(RuntimeError):
    """Raised when no governed provider/model route is certified."""


def _fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class HardwareProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    machine: str = Field(min_length=1, max_length=160)
    cpu: str = Field(min_length=1, max_length=320)
    gpu_devices: tuple[str, ...] = ()
    gpu_memory_mb: tuple[int, ...] = ()
    system_memory_mb: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_gpu_memory(self) -> HardwareProfile:
        if self.gpu_memory_mb and len(self.gpu_memory_mb) != len(self.gpu_devices):
            raise ValueError("GPU_MEMORY_DEVICE_COUNT_MISMATCH")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class WorkloadProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_class: str = Field(min_length=1, max_length=160)
    workload_class: str = Field(min_length=1, max_length=160)
    prompt_tokens_estimate: int = Field(ge=1)
    min_context_length: int = Field(ge=1)
    requires_structured_output: bool = False
    requires_tools: bool = False
    max_latency_ms: int = Field(gt=0)
    total_deadline_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_deadline(self) -> WorkloadProfile:
        if self.max_latency_ms > self.total_deadline_ms:
            raise ValueError("ATTEMPT_LATENCY_EXCEEDS_TOTAL_DEADLINE")
        return self
    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class ModelCapabilityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = "ollama"
    provider_version: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=240)
    hardware_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    workload_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    success: bool
    latency_ms: float = Field(ge=0)
    context_length: int = Field(ge=0)
    structured_output: bool = False
    tools: bool = False
    prompt_eval_count: int = Field(ge=0, default=0)
    prompt_tokens_per_second: float = Field(ge=0, default=0.0)
    eval_count: int = Field(ge=0, default=0)
    tokens_per_second: float = Field(ge=0, default=0.0)
    failure_reason: str | None = None


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str
    provider_version: str
    model: str
    hardware_fingerprint: str
    workload_fingerprint: str
    evidence_index: int
    authority_expanded: bool = False


def _is_local_model_name(model: str) -> bool:
    normalized = model.strip().lower()
    return bool(normalized) and not normalized.endswith(":cloud")


def select_certified_local_route(
    evidence: list[ModelCapabilityEvidence],
    *,
    hardware: HardwareProfile,
    workload: WorkloadProfile,
    current_provider_version: str,
    eligible_models: tuple[str, ...],
) -> RouteDecision:
    if not current_provider_version.strip():
        raise ProviderCapabilityError("PROVIDER_VERSION_REQUIRED")
    if not eligible_models:
        raise ProviderCapabilityError("ELIGIBLE_MODEL_SET_REQUIRED")

    hardware_fingerprint = hardware.fingerprint
    workload_fingerprint = workload.fingerprint

    for model in eligible_models:
        if not _is_local_model_name(model):
            continue
        for index, item in enumerate(evidence):
            if item.provider_id != "ollama":
                continue
            if item.model != model:
                continue
            if item.provider_version != current_provider_version:
                continue
            if item.hardware_fingerprint != hardware_fingerprint:
                continue
            if item.workload_fingerprint != workload_fingerprint:
                continue
            if not item.success:
                continue
            if item.latency_ms > workload.max_latency_ms:
                continue
            if item.context_length < workload.min_context_length:
                continue
            if workload.requires_structured_output and not item.structured_output:
                continue
            if workload.requires_tools and not item.tools:
                continue
            return RouteDecision(
                provider_id=item.provider_id,
                provider_version=item.provider_version,
                model=item.model,
                hardware_fingerprint=hardware_fingerprint,
                workload_fingerprint=workload_fingerprint,
                evidence_index=index,
            )

    raise ProviderCapabilityError("NO_LOCAL_MODEL_CERTIFIED_FOR_WORKLOAD")
