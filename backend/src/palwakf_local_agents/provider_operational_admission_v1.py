from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderContractEnvelopeV1,
    ProviderRuntimeRegistryV1,
)


ProbeName = Literal[
    "hermes_version",
    "hermes_serve_help",
    "opencode_version",
    "opencode_help",
    "playwright_version",
    "playwright_help",
]

ProviderId = Literal["hermes-headless", "opencode", "playwright"]


class ProviderProbeEvidenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: ProviderId
    probe_name: ProbeName
    success: bool
    exit_code: int
    version: str | None = Field(default=None, max_length=160)
    observed_at: datetime
    evidence_ref: str = Field(min_length=1, max_length=500)
    locality: Literal["LOCAL"] = "LOCAL"
    mutation_performed: Literal[False] = False
    network_write: Literal[False] = False

    @model_validator(mode="after")
    def validate_probe(self) -> ProviderProbeEvidenceV1:
        if self.success != (self.exit_code == 0):
            raise ValueError("PROBE_SUCCESS_EXIT_CODE_MISMATCH")
        if self.probe_name.endswith("_version") and self.success and not (self.version or "").strip():
            raise ValueError("SUCCESSFUL_VERSION_PROBE_REQUIRES_VERSION")
        return self


class ProviderProbePolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hermes: str = Field(min_length=1, max_length=500)
    opencode: str = Field(min_length=1, max_length=500)
    playwright: str = Field(min_length=1, max_length=500)


class RuntimeAdmissionEvidenceBundleV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    schema_name: Literal[
        "palwakf.provider_runtime_admission.evidence.v1"
    ] = Field(alias="schema", serialization_alias="schema")
    evidence_file_ref: str = Field(min_length=1, max_length=500)
    probes: tuple[ProviderProbeEvidenceV1, ...] = Field(min_length=6, max_length=12)
    secrets_captured: Literal[False] = False
    source_mutation: Literal[False] = False
    production_mutation: Literal[False] = False
    probe_policy: ProviderProbePolicyV1 | None = None

    def probe(self, name: ProbeName) -> ProviderProbeEvidenceV1:
        matches = [item for item in self.probes if item.probe_name == name]
        if len(matches) != 1:
            raise ValueError(f"PROBE_EVIDENCE_CARDINALITY:{name}:{len(matches)}")
        return matches[0]


class RuntimeProviderAdmissionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hermes: ProviderContractEnvelopeV1
    opencode: ProviderContractEnvelopeV1
    playwright: ProviderContractEnvelopeV1
    hermes_headless_admitted: Literal[True] = True
    opencode_bound_not_admitted: Literal[True] = True
    playwright_bound_not_admitted: Literal[True] = True
    no_authority_expansion: Literal[True] = True
    hermes_bounded_write_admitted: Literal[False] = False


_EXPECTED_PROVIDER: dict[ProbeName, ProviderId] = {
    "hermes_version": "hermes-headless",
    "hermes_serve_help": "hermes-headless",
    "opencode_version": "opencode",
    "opencode_help": "opencode",
    "playwright_version": "playwright",
    "playwright_help": "playwright",
}


def _require_probe(
    bundle: RuntimeAdmissionEvidenceBundleV1,
    name: ProbeName,
) -> ProviderProbeEvidenceV1:
    item = bundle.probe(name)
    if item.provider_id != _EXPECTED_PROVIDER[name]:
        raise ValueError(f"PROBE_PROVIDER_MISMATCH:{name}")
    if not item.success:
        raise ValueError(f"PROBE_NOT_SUCCESSFUL:{name}")
    if item.mutation_performed or item.network_write:
        raise ValueError(f"PROBE_MUST_BE_LOCAL_READ_ONLY:{name}")
    return item


def apply_runtime_admission_bundle_v1(
    bundle: RuntimeAdmissionEvidenceBundleV1,
    *,
    registry: ProviderRuntimeRegistryV1 | None = None,
) -> RuntimeProviderAdmissionResultV1:
    registry = registry or ProviderRuntimeRegistryV1()

    hermes_version = _require_probe(bundle, "hermes_version")
    hermes_surface = _require_probe(bundle, "hermes_serve_help")
    opencode_version = _require_probe(bundle, "opencode_version")
    _require_probe(bundle, "opencode_help")
    playwright_version = _require_probe(bundle, "playwright_version")
    _require_probe(bundle, "playwright_help")

    registry.record_probe(
        "hermes-headless",
        healthy=True,
        version=hermes_version.version,
        evidence_ref=hermes_version.evidence_ref,
    )
    registry.record_benchmark(
        "hermes-headless",
        success=True,
        evidence_ref=hermes_surface.evidence_ref,
    )
    registry.admit(
        "hermes-headless",
        evidence_ref=bundle.evidence_file_ref,
        admitted_capabilities=("agent.headless_api", "provider.health"),
        bounded_write=False,
    )

    registry.record_probe(
        "opencode",
        healthy=True,
        version=opencode_version.version,
        evidence_ref=bundle.evidence_file_ref,
    )
    registry.record_probe(
        "playwright",
        healthy=True,
        version=playwright_version.version,
        evidence_ref=bundle.evidence_file_ref,
    )

    provenance = (bundle.evidence_file_ref, "runtime-admission-v1")
    return RuntimeProviderAdmissionResultV1(
        hermes=registry.contract_envelope(
            "hermes-headless",
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="HERMES-HEADLESS-ADMISSION-V1",
            correlation_id="hermes-headless-admission-v1",
            provenance=provenance,
            created_at=hermes_surface.observed_at,
        ),
        opencode=registry.contract_envelope(
            "opencode",
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="OPENCODE-RUNTIME-BINDING-V1",
            correlation_id="opencode-runtime-binding-v1",
            provenance=provenance,
            created_at=opencode_version.observed_at,
        ),
        playwright=registry.contract_envelope(
            "playwright",
            project_id="PALWAKF_AGENTIC_AI_SYSTEM",
            task_id="PLAYWRIGHT-RUNTIME-BINDING-V1",
            correlation_id="playwright-runtime-binding-v1",
            provenance=provenance,
            created_at=playwright_version.observed_at,
        ),
    )
