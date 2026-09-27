from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from palwakf_local_agents.provider_operational_admission_v1 import (
    ProviderProbeEvidenceV1,
    RuntimeAdmissionEvidenceBundleV1,
    apply_runtime_admission_bundle_v1,
)
from palwakf_local_agents.provider_runtime_registry_v1 import (
    ProviderLifecycleState,
    ProviderRoutingError,
    ProviderRuntimeRegistryV1,
)

NOW = datetime(2026, 9, 27, 20, 0, tzinfo=UTC)
EVIDENCE = "evidence/runtime_provider_admission_v1/runtime-evidence.json"


def probe(provider_id: str, name: str, *, version: str | None = None):
    return ProviderProbeEvidenceV1(
        provider_id=provider_id,
        probe_name=name,
        success=True,
        exit_code=0,
        version=version,
        observed_at=NOW,
        evidence_ref=f"{EVIDENCE}#{name}",
    )


def bundle() -> RuntimeAdmissionEvidenceBundleV1:
    return RuntimeAdmissionEvidenceBundleV1(
        schema="palwakf.provider_runtime_admission.evidence.v1",
        evidence_file_ref=EVIDENCE,
        probes=(
            probe("hermes-headless", "hermes_version", version="0.21.4"),
            probe("hermes-headless", "hermes_serve_help"),
            probe("opencode", "opencode_version", version="2.0.18"),
            probe("opencode", "opencode_help"),
            probe("playwright", "playwright_version", version="1.57.0"),
            probe("playwright", "playwright_help"),
        ),
    )


def test_hermes_is_admitted_only_for_headless_api_and_health() -> None:
    registry = ProviderRuntimeRegistryV1()
    result = apply_runtime_admission_bundle_v1(bundle(), registry=registry)
    state = registry.get("hermes-headless")

    assert state.lifecycle == ProviderLifecycleState.admitted
    assert state.admitted_capabilities == ("agent.headless_api", "provider.health")
    assert state.bounded_write_admitted is False
    assert result.hermes.route_eligible is True

    assert registry.select_route("agent.headless_api").provider_id == "hermes-headless"
    with pytest.raises(
        ProviderRoutingError,
        match="NO_ADMITTED_PROVIDER_FOR_CAPABILITY",
    ):
        registry.select_route(
            "engineering.analysis",
            preferred_order=("hermes-headless",),
        )


def test_opencode_and_playwright_are_bound_but_not_admitted() -> None:
    registry = ProviderRuntimeRegistryV1()
    result = apply_runtime_admission_bundle_v1(bundle(), registry=registry)

    assert registry.get("opencode").lifecycle == ProviderLifecycleState.probed
    assert registry.get("playwright").lifecycle == ProviderLifecycleState.probed
    assert registry.get("opencode").admitted_capabilities == ()
    assert registry.get("playwright").admitted_capabilities == ()
    assert result.opencode.route_eligible is False
    assert result.playwright.route_eligible is False

    with pytest.raises(ProviderRoutingError):
        registry.select_route("engineering.analysis", preferred_order=("opencode",))
    with pytest.raises(ProviderRoutingError):
        registry.select_route("browser.uat", preferred_order=("playwright",))


def test_contract_envelope_exposes_canonical_provider_metadata() -> None:
    result = apply_runtime_admission_bundle_v1(bundle())
    hermes = result.hermes

    assert hermes.provider_kind == "GENERAL_AGENT"
    assert hermes.version == "0.21.4"
    assert hermes.read_write_class == "BOUNDED_WRITE_CAPABLE"
    assert hermes.bounded_write_admitted is False
    assert hermes.admitted_capabilities == ("agent.headless_api", "provider.health")
    assert hermes.admission_evidence == (EVIDENCE,)


def test_mutating_probe_evidence_is_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        ProviderProbeEvidenceV1.model_validate(
            {
                "provider_id": "hermes-headless",
                "probe_name": "hermes_version",
                "success": True,
                "exit_code": 0,
                "version": "0.21.4",
                "observed_at": NOW,
                "evidence_ref": "evidence",
                "mutation_performed": True,
            }
        )


def test_probe_provider_identity_mismatch_fails_closed() -> None:
    data = bundle().model_dump(mode="python")
    probes = list(data["probes"])
    probes[0] = dict(probes[0])
    probes[0]["provider_id"] = "opencode"
    data["probes"] = probes

    with pytest.raises(ValueError, match="PROBE_PROVIDER_MISMATCH"):
        apply_runtime_admission_bundle_v1(
            RuntimeAdmissionEvidenceBundleV1.model_validate(data)
        )
