from __future__ import annotations

from pathlib import Path

from palwakf_local_agents.codex_provider_v1 import (
    CodexEngineeringProviderV1,
    CodexProviderSettingsV1,
    _safe_environment,
)
from palwakf_local_agents.outbound_capabilities_v1 import (
    default_capability_registry_v1,
)


def test_codex_environment_removes_normal_api_key_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "forbidden")
    monkeypatch.setenv("CODEX_API_KEY", "forbidden")

    environment = _safe_environment()

    assert "OPENAI_API_KEY" not in environment
    assert "CODEX_API_KEY" not in environment


def test_codex_readiness_fails_closed_when_binary_is_missing(
    tmp_path: Path,
) -> None:
    provider = CodexEngineeringProviderV1(
        CodexProviderSettingsV1(
            executable=str(tmp_path / "missing-codex.exe"),
        )
    )

    readiness = provider.readiness()

    assert readiness["state"] == "NOT_READY"
    assert readiness["reason"] == "CODEX_EXECUTABLE_NOT_FOUND"


def test_registry_exposes_governed_codex_surface_without_live_provider() -> None:
    registry = default_capability_registry_v1(codex_provider=None)

    assert registry.resolve("engineering.codex.readiness").mutation_class == "READ_ONLY"
    assert registry.resolve("engineering.codex.analyze").mutation_class == "READ_ONLY"
    assert registry.resolve("engineering.codex.plan").mutation_class == "READ_ONLY"
    assert registry.resolve("engineering.codex.review_diff").mutation_class == "READ_ONLY"
    assert registry.resolve("engineering.codex.edit_bounded").mutation_class == "SOURCE_WRITE"
    assert registry.resolve("engineering.codex.test").mutation_class == "TEMP_MUTATION"
    assert registry.resolve("engineering.codex.debug").mutation_class == "TEMP_MUTATION"
