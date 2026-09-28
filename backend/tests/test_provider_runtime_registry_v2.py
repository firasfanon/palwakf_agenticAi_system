from datetime import UTC, datetime

import pytest

from palwakf_local_agents.provider_runtime_registry_v1 import ProviderRoutingError
from palwakf_local_agents.provider_runtime_registry_v2 import (
    REMOTE_CAPABILITY_IDS_V2,
    ProviderRuntimeRegistryV2,
)


def test_remote_transport_lifecycle_preserves_exact_ten() -> None:
    registry = ProviderRuntimeRegistryV2()
    initial = registry.snapshot()
    assert initial.route_eligible is False
    assert initial.provider_kind == "EXECUTION_TRANSPORT"
    assert initial.authority_scope == "NO_SOVEREIGN_AUTHORITY"
    assert initial.transport_only is True
    assert initial.arbitrary_shell_exposed is False
    assert initial.bounded_source_write_admitted is False
    assert len(initial.capabilities) == 10

    registry.record_probe(
        healthy=True,
        version="bootstrap-proven",
        endpoint="mcp://palwakf-remote",
        evidence_ref="evidence://probe",
    )
    registry.record_benchmark(success=True, evidence_ref="evidence://benchmark")
    admitted = registry.admit(
        evidence_ref="evidence://admission",
        admitted_capabilities=REMOTE_CAPABILITY_IDS_V2,
    )
    assert admitted.route_eligible is True
    assert admitted.admitted_capabilities == REMOTE_CAPABILITY_IDS_V2


def test_remote_transport_refuses_partial_or_unknown_admission() -> None:
    registry = ProviderRuntimeRegistryV2()
    registry.record_probe(
        healthy=True,
        version="bootstrap-proven",
        endpoint=None,
        evidence_ref="evidence://probe",
    )
    registry.record_benchmark(success=True, evidence_ref="evidence://benchmark")

    with pytest.raises(ProviderRoutingError, match="EXACT_TEN"):
        registry.admit(
            evidence_ref="evidence://admission",
            admitted_capabilities=("mesh_hostname",),
        )


def test_contract_envelope_has_no_sovereign_authority() -> None:
    registry = ProviderRuntimeRegistryV2()
    registry.record_probe(
        healthy=True,
        version="bootstrap-proven",
        endpoint=None,
        evidence_ref="evidence://probe",
    )
    registry.record_benchmark(success=True, evidence_ref="evidence://benchmark")
    registry.admit(
        evidence_ref="evidence://admission",
        admitted_capabilities=REMOTE_CAPABILITY_IDS_V2,
    )
    envelope = registry.contract_envelope(
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        task_id="AUTONOMOUS-EXECUTION-CHANNEL-BINDING-V1",
        correlation_id="autonomous-execution-channel-binding-v1",
        provenance=("test",),
        created_at=datetime.now(UTC),
    )
    assert envelope.provider_kind == "EXECUTION_TRANSPORT"
    assert envelope.authority_scope == "NO_SOVEREIGN_AUTHORITY"
    assert envelope.route_eligible is True
    assert envelope.transport_only is True
    assert envelope.arbitrary_shell_exposed is False
