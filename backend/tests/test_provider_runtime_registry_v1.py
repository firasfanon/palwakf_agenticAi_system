from datetime import UTC, datetime

import pytest

from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderHealthState,
    ProviderLifecycleState,
    ProviderRoutingError,
    ProviderRuntimeRegistryV1,
)


NOW = datetime(2026, 9, 27, 18, 50, tzinfo=UTC)


def admit(
    registry: ProviderRuntimeRegistryV1,
    provider_id: str,
    *,
    bounded_write: bool = False,
) -> None:
    registry.record_probe(
        provider_id,
        healthy=True,
        version="test-version",
        evidence_ref=f"{provider_id}:probe",
    )
    registry.record_benchmark(
        provider_id,
        success=True,
        evidence_ref=f"{provider_id}:benchmark",
    )
    registry.admit(
        provider_id,
        evidence_ref=f"{provider_id}:admission",
        bounded_write=bounded_write,
    )


def test_default_registry_contains_required_runtime_providers() -> None:
    registry = ProviderRuntimeRegistryV1()
    states = {item.provider_id: item for item in registry.snapshot()}

    assert set(states) == {
        "ollama",
        "hermes-headless",
        "opencode",
        "playwright",
    }
    assert all(item.lifecycle == ProviderLifecycleState.discovered for item in states.values())
    assert all(item.route_eligible is False for item in states.values())
    assert states["hermes-headless"].bounded_write_admitted is False
    assert states["opencode"].bounded_write_admitted is False


def test_unadmitted_provider_is_never_routed() -> None:
    registry = ProviderRuntimeRegistryV1()
    registry.record_probe(
        "opencode",
        healthy=True,
        version="2.0.18",
        evidence_ref="opencode:probe",
    )

    with pytest.raises(
        ProviderRoutingError,
        match="NO_ADMITTED_PROVIDER_FOR_CAPABILITY",
    ):
        registry.select_route(
            "engineering.analysis",
            preferred_order=("opencode",),
        )


def test_provider_lifecycle_requires_probe_benchmark_then_admission() -> None:
    registry = ProviderRuntimeRegistryV1()

    with pytest.raises(
        ProviderRoutingError,
        match="PROVIDER_MUST_BE_BENCHMARKED_BEFORE_ADMISSION",
    ):
        registry.admit("ollama", evidence_ref="invalid-admission")

    probed = registry.record_probe(
        "ollama",
        healthy=True,
        version="0.34.3",
        endpoint="http://127.0.0.1:11434",
        evidence_ref="ollama:probe",
    )
    assert probed.lifecycle == ProviderLifecycleState.probed
    assert probed.health == ProviderHealthState.healthy

    benchmarked = registry.record_benchmark(
        "ollama",
        success=True,
        evidence_ref="ollama:benchmark",
    )
    assert benchmarked.lifecycle == ProviderLifecycleState.benchmarked

    admitted = registry.admit(
        "ollama",
        evidence_ref="ollama:admission",
    )
    assert admitted.lifecycle == ProviderLifecycleState.admitted
    assert admitted.route_eligible is True

    route = registry.select_route(
        "model.inference",
        preferred_order=("ollama",),
    )
    assert route.provider_id == "ollama"


def test_hermes_bounded_write_is_not_implicitly_admitted() -> None:
    registry = ProviderRuntimeRegistryV1()
    admit(registry, "hermes-headless", bounded_write=False)

    state = registry.get("hermes-headless")
    assert state.route_eligible is True
    assert state.bounded_write_admitted is False


def test_quarantine_removes_provider_from_routing() -> None:
    registry = ProviderRuntimeRegistryV1()
    admit(registry, "opencode")

    quarantined = registry.quarantine(
        "opencode",
        evidence_ref="opencode:security-boundary-failed",
    )
    assert quarantined.health == ProviderHealthState.quarantined
    assert quarantined.route_eligible is False

    with pytest.raises(
        ProviderRoutingError,
        match="NO_ADMITTED_PROVIDER_FOR_CAPABILITY",
    ):
        registry.select_route(
            "engineering.test",
            preferred_order=("opencode",),
        )


def test_failure_falls_back_only_to_another_admitted_healthy_provider() -> None:
    registry = ProviderRuntimeRegistryV1()
    admit(registry, "opencode")
    admit(registry, "hermes-headless")

    failure = registry.record_failure(
        "opencode",
        failure_id="failure-1",
        capability="engineering.analysis",
        failure_class="TRANSIENT_PROVIDER_ERROR",
        retryable=True,
        evidence_ref="opencode:failure",
        preferred_fallback_order=("hermes-headless",),
    )

    assert failure.resulting_health == ProviderHealthState.degraded
    assert failure.fallback_provider_id == "hermes-headless"
    assert failure.no_authority_expansion is True


def test_contract_envelope_matches_cross_system_provider_descriptor_shape() -> None:
    registry = ProviderRuntimeRegistryV1()
    admit(registry, "playwright")

    envelope = registry.contract_envelope(
        "playwright",
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        task_id="RUNTIME-PROVIDER-V1",
        correlation_id="corr-1",
        provenance=("playwright:uat-readback",),
        created_at=NOW,
    )

    assert envelope.schema_version == "1.0"
    assert envelope.compatibility_version == "1"
    assert envelope.contract_type == "ProviderDescriptor"
    assert envelope.authority_scope == "NO_SOVEREIGN_AUTHORITY"
    assert envelope.producer == "Agentic"
    assert envelope.lifecycle == ProviderLifecycleState.admitted
    assert envelope.health == ProviderHealthState.healthy
    assert envelope.route_eligible is True
