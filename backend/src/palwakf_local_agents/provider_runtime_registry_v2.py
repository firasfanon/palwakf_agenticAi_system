from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderHealthState,
    ProviderLifecycleState,
    ProviderRoutingError,
)


REMOTE_CAPABILITY_IDS_V2: tuple[str, ...] = (
    "mesh_device_info",
    "mesh_hostname",
    "file_read",
    "temp_write",
    "temp_delete",
    "bounded_powershell",
    "process_port_readback",
    "git_readback",
    "playwright_screenshot_uat",
    "audit_readback",
)


class RemoteTransportProviderStateV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: Literal["palwakf-remote-mcp"] = "palwakf-remote-mcp"
    display_name: Literal["PalWakf Remote MCP"] = "PalWakf Remote MCP"
    provider_kind: Literal["EXECUTION_TRANSPORT"] = "EXECUTION_TRANSPORT"
    authority_scope: Literal["NO_SOVEREIGN_AUTHORITY"] = "NO_SOVEREIGN_AUTHORITY"
    transport_only: Literal[True] = True
    arbitrary_shell_exposed: Literal[False] = False
    bounded_source_write_admitted: Literal[False] = False
    version: str | None = Field(default=None, max_length=160)
    endpoint: str | None = Field(default=None, max_length=500)
    capabilities: tuple[str, ...] = REMOTE_CAPABILITY_IDS_V2
    admitted_capabilities: tuple[str, ...] = ()
    lifecycle: ProviderLifecycleState = ProviderLifecycleState.discovered
    health: ProviderHealthState = ProviderHealthState.unavailable
    probe_evidence: tuple[str, ...] = ()
    benchmark_evidence: tuple[str, ...] = ()
    admission_evidence: tuple[str, ...] = ()
    health_evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_state(self) -> "RemoteTransportProviderStateV2":
        if tuple(self.capabilities) != REMOTE_CAPABILITY_IDS_V2:
            raise ValueError("REMOTE_TRANSPORT_MUST_PRESERVE_EXACT_TEN_CAPABILITIES")
        if len(set(self.admitted_capabilities)) != len(self.admitted_capabilities):
            raise ValueError("REMOTE_TRANSPORT_ADMITTED_CAPABILITIES_MUST_BE_UNIQUE")
        if any(x not in REMOTE_CAPABILITY_IDS_V2 for x in self.admitted_capabilities):
            raise ValueError("REMOTE_TRANSPORT_UNKNOWN_ADMITTED_CAPABILITY")
        if self.lifecycle == ProviderLifecycleState.probed and not self.probe_evidence:
            raise ValueError("PROBED_REMOTE_TRANSPORT_REQUIRES_PROBE_EVIDENCE")
        if self.lifecycle == ProviderLifecycleState.benchmarked:
            if not self.probe_evidence or not self.benchmark_evidence:
                raise ValueError("BENCHMARKED_REMOTE_TRANSPORT_REQUIRES_EVIDENCE")
        if self.lifecycle == ProviderLifecycleState.admitted:
            if (
                not self.probe_evidence
                or not self.benchmark_evidence
                or not self.admission_evidence
            ):
                raise ValueError("ADMITTED_REMOTE_TRANSPORT_REQUIRES_COMPLETE_EVIDENCE")
            if tuple(self.admitted_capabilities) != REMOTE_CAPABILITY_IDS_V2:
                raise ValueError("REMOTE_TRANSPORT_ADMISSION_MUST_PRESERVE_ALL_TEN")
        elif self.admitted_capabilities:
            raise ValueError("NON_ADMITTED_REMOTE_TRANSPORT_CANNOT_HAVE_ADMITTED_CAPS")
        return self

    @property
    def route_eligible(self) -> bool:
        return (
            self.lifecycle == ProviderLifecycleState.admitted
            and self.health == ProviderHealthState.healthy
            and tuple(self.admitted_capabilities) == REMOTE_CAPABILITY_IDS_V2
        )


class RemoteTransportProviderEnvelopeV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0"] = "2.0"
    compatibility_version: Literal["1"] = "1"
    contract_type: Literal["ProviderDescriptor"] = "ProviderDescriptor"
    project_id: str
    task_id: str
    correlation_id: str
    authority_scope: Literal["NO_SOVEREIGN_AUTHORITY"] = "NO_SOVEREIGN_AUTHORITY"
    producer: Literal["Agentic"] = "Agentic"
    created_at: datetime
    provenance: tuple[str, ...] = Field(min_length=1, max_length=64)
    provider_id: Literal["palwakf-remote-mcp"] = "palwakf-remote-mcp"
    provider_kind: Literal["EXECUTION_TRANSPORT"] = "EXECUTION_TRANSPORT"
    lifecycle: ProviderLifecycleState
    health: ProviderHealthState
    capabilities: tuple[str, ...]
    admitted_capabilities: tuple[str, ...]
    route_eligible: bool
    transport_only: Literal[True] = True
    arbitrary_shell_exposed: Literal[False] = False
    bounded_source_write_admitted: Literal[False] = False


class ProviderRuntimeRegistryV2:
    def __init__(self, state: RemoteTransportProviderStateV2 | None = None) -> None:
        self._state = state or RemoteTransportProviderStateV2()

    def snapshot(self) -> RemoteTransportProviderStateV2:
        return self._state

    def record_probe(
        self,
        *,
        healthy: bool,
        version: str,
        endpoint: str | None,
        evidence_ref: str,
    ) -> RemoteTransportProviderStateV2:
        self._state = self._state.model_copy(
            update={
                "version": version,
                "endpoint": endpoint,
                "lifecycle": ProviderLifecycleState.probed,
                "health": (
                    ProviderHealthState.healthy
                    if healthy
                    else ProviderHealthState.unavailable
                ),
                "probe_evidence": (evidence_ref,),
                "benchmark_evidence": (),
                "admission_evidence": (),
                "admitted_capabilities": (),
                "health_evidence": (evidence_ref,),
            }
        )
        self._state = RemoteTransportProviderStateV2.model_validate(
            self._state.model_dump()
        )
        return self._state

    def record_benchmark(
        self, *, success: bool, evidence_ref: str
    ) -> RemoteTransportProviderStateV2:
        current = self._state
        if not current.probe_evidence:
            raise ProviderRoutingError("REMOTE_TRANSPORT_BENCHMARK_REQUIRES_PROBE")
        self._state = current.model_copy(
            update={
                "lifecycle": (
                    ProviderLifecycleState.benchmarked
                    if success
                    else ProviderLifecycleState.probed
                ),
                "health": (
                    ProviderHealthState.healthy
                    if success
                    else ProviderHealthState.degraded
                ),
                "benchmark_evidence": (evidence_ref,) if success else (),
                "admission_evidence": (),
                "admitted_capabilities": (),
            }
        )
        self._state = RemoteTransportProviderStateV2.model_validate(
            self._state.model_dump()
        )
        return self._state

    def admit(
        self, *, evidence_ref: str, admitted_capabilities: tuple[str, ...]
    ) -> RemoteTransportProviderStateV2:
        current = self._state
        if current.lifecycle != ProviderLifecycleState.benchmarked:
            raise ProviderRoutingError("REMOTE_TRANSPORT_ADMISSION_REQUIRES_BENCHMARK")
        if current.health != ProviderHealthState.healthy:
            raise ProviderRoutingError("REMOTE_TRANSPORT_ADMISSION_REQUIRES_HEALTH")
        if tuple(admitted_capabilities) != REMOTE_CAPABILITY_IDS_V2:
            raise ProviderRoutingError("REMOTE_TRANSPORT_MUST_ADMIT_EXACT_TEN")
        self._state = current.model_copy(
            update={
                "lifecycle": ProviderLifecycleState.admitted,
                "admitted_capabilities": admitted_capabilities,
                "admission_evidence": (evidence_ref,),
            }
        )
        self._state = RemoteTransportProviderStateV2.model_validate(
            self._state.model_dump()
        )
        return self._state

    def contract_envelope(
        self,
        *,
        project_id: str,
        task_id: str,
        correlation_id: str,
        provenance: tuple[str, ...],
        created_at: datetime,
    ) -> RemoteTransportProviderEnvelopeV2:
        state = self._state
        return RemoteTransportProviderEnvelopeV2(
            project_id=project_id,
            task_id=task_id,
            correlation_id=correlation_id,
            created_at=created_at,
            provenance=provenance,
            lifecycle=state.lifecycle,
            health=state.health,
            capabilities=state.capabilities,
            admitted_capabilities=state.admitted_capabilities,
            route_eligible=state.route_eligible,
        )
