from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderRoutingError(RuntimeError):
    """Raised when no governed provider route is eligible."""


class ProviderLifecycleState(StrEnum):
    discovered = "DISCOVERED"
    probed = "PROBED"
    benchmarked = "BENCHMARKED"
    admitted = "ADMITTED"


class ProviderHealthState(StrEnum):
    healthy = "HEALTHY"
    degraded = "DEGRADED"
    unavailable = "UNAVAILABLE"
    quarantined = "QUARANTINED"


class ProviderRuntimeStateV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{1,79}$")
    display_name: str = Field(min_length=1, max_length=160)
    provider_kind: Literal[
        "MODEL_RUNTIME",
        "GENERAL_AGENT",
        "ENGINEERING",
        "BROWSER_UAT",
    ]
    version: str | None = Field(default=None, max_length=160)
    endpoint: str | None = Field(default=None, max_length=500)
    capabilities: tuple[str, ...] = Field(min_length=1, max_length=64)
    lifecycle: ProviderLifecycleState = ProviderLifecycleState.discovered
    health: ProviderHealthState = ProviderHealthState.unavailable
    read_write_class: Literal[
        "MODEL_INFERENCE",
        "READ_ONLY",
        "BOUNDED_WRITE_CAPABLE",
        "BROWSER_UAT",
    ]
    bounded_write_admitted: bool = False
    probe_evidence: tuple[str, ...] = ()
    benchmark_evidence: tuple[str, ...] = ()
    admission_evidence: tuple[str, ...] = ()
    health_evidence: tuple[str, ...] = ()
    authority_scope: Literal["NO_SOVEREIGN_AUTHORITY"] = "NO_SOVEREIGN_AUTHORITY"

    @model_validator(mode="after")
    def validate_state(self) -> ProviderRuntimeStateV1:
        evidence_sets = (
            self.probe_evidence,
            self.benchmark_evidence,
            self.admission_evidence,
            self.health_evidence,
        )
        if any(not item.strip() for values in evidence_sets for item in values):
            raise ValueError("PROVIDER_EVIDENCE_MUST_BE_NONEMPTY")
        if self.lifecycle == ProviderLifecycleState.probed and not self.probe_evidence:
            raise ValueError("PROBED_PROVIDER_REQUIRES_PROBE_EVIDENCE")
        if self.lifecycle == ProviderLifecycleState.benchmarked:
            if not self.probe_evidence or not self.benchmark_evidence:
                raise ValueError("BENCHMARKED_PROVIDER_REQUIRES_PROBE_AND_BENCHMARK")
        if self.lifecycle == ProviderLifecycleState.admitted:
            if (
                not self.probe_evidence
                or not self.benchmark_evidence
                or not self.admission_evidence
            ):
                raise ValueError("ADMITTED_PROVIDER_REQUIRES_COMPLETE_EVIDENCE")
        if self.bounded_write_admitted and self.read_write_class != "BOUNDED_WRITE_CAPABLE":
            raise ValueError("BOUNDED_WRITE_ADMISSION_REQUIRES_CAPABLE_PROVIDER")
        return self

    @property
    def route_eligible(self) -> bool:
        return (
            self.lifecycle == ProviderLifecycleState.admitted
            and self.health == ProviderHealthState.healthy
        )


class ProviderFailureV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_id: str = Field(min_length=1, max_length=160)
    provider_id: str
    capability: str = Field(min_length=1, max_length=160)
    failure_class: str = Field(min_length=1, max_length=160)
    retryable: bool
    evidence_ref: str = Field(min_length=1, max_length=500)
    resulting_health: ProviderHealthState
    fallback_provider_id: str | None = None
    authority_impact: Literal["NONE"] = "NONE"
    no_authority_expansion: Literal[True] = True


class ProviderContractEnvelopeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    compatibility_version: Literal["1"] = "1"
    contract_type: Literal["ProviderDescriptor"] = "ProviderDescriptor"
    project_id: str = Field(min_length=1, max_length=160)
    task_id: str = Field(min_length=1, max_length=160)
    correlation_id: str = Field(min_length=1, max_length=160)
    authority_scope: Literal["NO_SOVEREIGN_AUTHORITY"] = "NO_SOVEREIGN_AUTHORITY"
    producer: Literal["Agentic"] = "Agentic"
    created_at: datetime
    provenance: tuple[str, ...] = Field(min_length=1, max_length=64)
    provider_id: str
    lifecycle: ProviderLifecycleState
    health: ProviderHealthState
    capabilities: tuple[str, ...]
    route_eligible: bool

    @model_validator(mode="after")
    def validate_eligibility(self) -> ProviderContractEnvelopeV1:
        if self.route_eligible and not (
            self.lifecycle == ProviderLifecycleState.admitted
            and self.health == ProviderHealthState.healthy
        ):
            raise ValueError("ROUTE_ELIGIBLE_PROVIDER_MUST_BE_ADMITTED_AND_HEALTHY")
        return self


def default_provider_runtime_states_v1() -> tuple[ProviderRuntimeStateV1, ...]:
    return (
        ProviderRuntimeStateV1(
            provider_id="ollama",
            display_name="Ollama",
            provider_kind="MODEL_RUNTIME",
            capabilities=(
                "model.inference",
                "model.structured_output",
                "model.health",
                "model.list",
            ),
            read_write_class="MODEL_INFERENCE",
        ),
        ProviderRuntimeStateV1(
            provider_id="hermes-headless",
            display_name="Hermes Headless/API",
            provider_kind="GENERAL_AGENT",
            capabilities=(
                "agent.plan",
                "agent.tool_use",
                "agent.read_only_execution",
                "engineering.analysis",
                "provider.health",
            ),
            read_write_class="BOUNDED_WRITE_CAPABLE",
            bounded_write_admitted=False,
        ),
        ProviderRuntimeStateV1(
            provider_id="opencode",
            display_name="OpenCode",
            provider_kind="ENGINEERING",
            capabilities=(
                "engineering.analysis",
                "engineering.edit",
                "engineering.test",
                "provider.health",
            ),
            read_write_class="BOUNDED_WRITE_CAPABLE",
            bounded_write_admitted=False,
        ),
        ProviderRuntimeStateV1(
            provider_id="playwright",
            display_name="Playwright",
            provider_kind="BROWSER_UAT",
            capabilities=(
                "browser.uat",
                "browser.navigation",
                "browser.screenshot",
                "provider.health",
            ),
            read_write_class="BROWSER_UAT",
        ),
    )


class ProviderRuntimeRegistryV1:
    def __init__(
        self,
        states: tuple[ProviderRuntimeStateV1, ...] | None = None,
    ) -> None:
        items = states or default_provider_runtime_states_v1()
        self._states = {item.provider_id: item for item in items}
        if len(self._states) != len(items):
            raise ProviderRoutingError("DUPLICATE_PROVIDER_ID")

    def snapshot(self) -> tuple[ProviderRuntimeStateV1, ...]:
        return tuple(self._states[key] for key in sorted(self._states))

    def get(self, provider_id: str) -> ProviderRuntimeStateV1:
        try:
            return self._states[provider_id]
        except KeyError as exc:
            raise ProviderRoutingError(f"PROVIDER_UNKNOWN:{provider_id}") from exc

    def record_probe(
        self,
        provider_id: str,
        *,
        healthy: bool,
        version: str | None,
        evidence_ref: str,
        endpoint: str | None = None,
    ) -> ProviderRuntimeStateV1:
        current = self.get(provider_id)
        if current.health == ProviderHealthState.quarantined:
            raise ProviderRoutingError("QUARANTINED_PROVIDER_REQUIRES_READMISSION")
        next_state = current.model_copy(
            update={
                "version": version,
                "endpoint": endpoint or current.endpoint,
                "lifecycle": ProviderLifecycleState.probed,
                "health": (
                    ProviderHealthState.healthy
                    if healthy
                    else ProviderHealthState.unavailable
                ),
                "probe_evidence": (*current.probe_evidence, evidence_ref),
                "health_evidence": (*current.health_evidence, evidence_ref),
                "benchmark_evidence": (),
                "admission_evidence": (),
                "bounded_write_admitted": False,
            }
        )
        self._states[provider_id] = ProviderRuntimeStateV1.model_validate(
            next_state.model_dump(mode="python")
        )
        return self._states[provider_id]

    def record_benchmark(
        self,
        provider_id: str,
        *,
        success: bool,
        evidence_ref: str,
    ) -> ProviderRuntimeStateV1:
        current = self.get(provider_id)
        if current.lifecycle not in {
            ProviderLifecycleState.probed,
            ProviderLifecycleState.benchmarked,
            ProviderLifecycleState.admitted,
        }:
            raise ProviderRoutingError("PROVIDER_MUST_BE_PROBED_BEFORE_BENCHMARK")
        if current.health == ProviderHealthState.quarantined:
            raise ProviderRoutingError("QUARANTINED_PROVIDER_REQUIRES_READMISSION")
        if not success:
            next_state = current.model_copy(
                update={
                    "lifecycle": ProviderLifecycleState.probed,
                    "health": ProviderHealthState.degraded,
                    "benchmark_evidence": (*current.benchmark_evidence, evidence_ref),
                    "admission_evidence": (),
                    "bounded_write_admitted": False,
                }
            )
        else:
            next_state = current.model_copy(
                update={
                    "lifecycle": ProviderLifecycleState.benchmarked,
                    "benchmark_evidence": (*current.benchmark_evidence, evidence_ref),
                    "admission_evidence": (),
                    "bounded_write_admitted": False,
                }
            )
        self._states[provider_id] = ProviderRuntimeStateV1.model_validate(
            next_state.model_dump(mode="python")
        )
        return self._states[provider_id]

    def admit(
        self,
        provider_id: str,
        *,
        evidence_ref: str,
        bounded_write: bool = False,
    ) -> ProviderRuntimeStateV1:
        current = self.get(provider_id)
        if current.lifecycle != ProviderLifecycleState.benchmarked:
            raise ProviderRoutingError("PROVIDER_MUST_BE_BENCHMARKED_BEFORE_ADMISSION")
        if current.health != ProviderHealthState.healthy:
            raise ProviderRoutingError("ONLY_HEALTHY_PROVIDER_CAN_BE_ADMITTED")
        if bounded_write and current.read_write_class != "BOUNDED_WRITE_CAPABLE":
            raise ProviderRoutingError("PROVIDER_NOT_BOUNDED_WRITE_CAPABLE")
        next_state = current.model_copy(
            update={
                "lifecycle": ProviderLifecycleState.admitted,
                "admission_evidence": (*current.admission_evidence, evidence_ref),
                "bounded_write_admitted": bounded_write,
            }
        )
        self._states[provider_id] = ProviderRuntimeStateV1.model_validate(
            next_state.model_dump(mode="python")
        )
        return self._states[provider_id]

    def set_health(
        self,
        provider_id: str,
        health: ProviderHealthState,
        *,
        evidence_ref: str,
    ) -> ProviderRuntimeStateV1:
        current = self.get(provider_id)
        if health == ProviderHealthState.healthy and not current.probe_evidence:
            raise ProviderRoutingError("HEALTHY_PROVIDER_REQUIRES_PROBE_EVIDENCE")
        next_state = current.model_copy(
            update={
                "health": health,
                "health_evidence": (*current.health_evidence, evidence_ref),
                "bounded_write_admitted": (
                    current.bounded_write_admitted
                    if health != ProviderHealthState.quarantined
                    else False
                ),
            }
        )
        self._states[provider_id] = ProviderRuntimeStateV1.model_validate(
            next_state.model_dump(mode="python")
        )
        return self._states[provider_id]

    def quarantine(
        self,
        provider_id: str,
        *,
        evidence_ref: str,
    ) -> ProviderRuntimeStateV1:
        return self.set_health(
            provider_id,
            ProviderHealthState.quarantined,
            evidence_ref=evidence_ref,
        )

    def eligible(
        self,
        capability: str,
        *,
        allow_degraded: bool = False,
        exclude: frozenset[str] = frozenset(),
    ) -> tuple[ProviderRuntimeStateV1, ...]:
        allowed_health = {ProviderHealthState.healthy}
        if allow_degraded:
            allowed_health.add(ProviderHealthState.degraded)
        return tuple(
            item
            for item in self.snapshot()
            if item.provider_id not in exclude
            and capability in item.capabilities
            and item.lifecycle == ProviderLifecycleState.admitted
            and item.health in allowed_health
        )

    def select_route(
        self,
        capability: str,
        *,
        preferred_order: tuple[str, ...] = (),
        allow_degraded: bool = False,
        exclude: frozenset[str] = frozenset(),
    ) -> ProviderRuntimeStateV1:
        eligible = self.eligible(
            capability,
            allow_degraded=allow_degraded,
            exclude=exclude,
        )
        by_id = {item.provider_id: item for item in eligible}
        for provider_id in preferred_order:
            if provider_id in by_id:
                return by_id[provider_id]
        if eligible:
            return eligible[0]
        raise ProviderRoutingError(f"NO_ADMITTED_PROVIDER_FOR_CAPABILITY:{capability}")

    def record_failure(
        self,
        provider_id: str,
        *,
        failure_id: str,
        capability: str,
        failure_class: str,
        retryable: bool,
        evidence_ref: str,
        preferred_fallback_order: tuple[str, ...] = (),
    ) -> ProviderFailureV1:
        current = self.get(provider_id)
        resulting_health = (
            ProviderHealthState.degraded
            if retryable
            else ProviderHealthState.unavailable
        )
        self.set_health(
            provider_id,
            resulting_health,
            evidence_ref=evidence_ref,
        )
        fallback_provider_id: str | None = None
        try:
            fallback = self.select_route(
                capability,
                preferred_order=preferred_fallback_order,
                exclude=frozenset({provider_id}),
            )
            fallback_provider_id = fallback.provider_id
        except ProviderRoutingError:
            fallback_provider_id = None

        return ProviderFailureV1(
            failure_id=failure_id,
            provider_id=provider_id,
            capability=capability,
            failure_class=failure_class,
            retryable=retryable,
            evidence_ref=evidence_ref,
            resulting_health=resulting_health,
            fallback_provider_id=fallback_provider_id,
        )

    def contract_envelope(
        self,
        provider_id: str,
        *,
        project_id: str,
        task_id: str,
        correlation_id: str,
        provenance: tuple[str, ...],
        created_at: datetime | None = None,
    ) -> ProviderContractEnvelopeV1:
        item = self.get(provider_id)
        return ProviderContractEnvelopeV1(
            project_id=project_id,
            task_id=task_id,
            correlation_id=correlation_id,
            created_at=created_at or datetime.now(UTC),
            provenance=provenance,
            provider_id=item.provider_id,
            lifecycle=item.lifecycle,
            health=item.health,
            capabilities=item.capabilities,
            route_eligible=item.route_eligible,
        )
