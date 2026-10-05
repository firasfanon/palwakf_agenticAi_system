from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from palwakf_local_agents.ui_ux_design_intelligence_v1 import (
    DESIGN_INTELLIGENCE_ID,
    PROVIDER_PINNED_HEAD,
    ProviderIntegrityError,
    provider_metadata,
    provider_runtime_policy_v1,
    recommend_design_system,
    search_domain,
    search_stack,
    verify_provider_snapshot,
)
from palwakf_local_agents.ui_ux_design_intelligence_v1 import provider as provider_module


def test_provider_snapshot_exact_integrity_and_no_execution_authority() -> None:
    result = verify_provider_snapshot()
    assert result["integrity"] == "PASS"
    assert result["pinned_head"] == PROVIDER_PINNED_HEAD
    assert result["file_count"] == 44
    assert result["execution_authority"] == "NONE"
    assert result["persistence_authority"] == "NONE"
    assert result["network_authority"] == "NONE"
    assert result["runtime_materialization"] == "BOUNDED_EPHEMERAL_TEMP_ONLY"


def test_provider_metadata_preserves_palwakf_identity_authority() -> None:
    result = provider_metadata()
    assert result["design_intelligence_id"] == DESIGN_INTELLIGENCE_ID
    assert result["license"] == "MIT"
    assert result["identity_policy"]["direction"] == "RTL"
    assert result["identity_policy"]["palette_baseline"] == "navy_gold"
    assert result["identity_policy"]["provider_palette_authority"] is False
    assert result["identity_policy"]["provider_typography_authority"] is False
    assert result["identity_policy"]["visual_creativity"].startswith("BROAD")


def test_runtime_policy_admits_design_intelligence_but_not_execution() -> None:
    policy = provider_runtime_policy_v1()
    assert policy["advisory_only"] is True
    assert policy["remote_capability_admitted"] is False
    assert "data/**" in policy["allowed"]
    assert "scripts/search.py" not in policy["allowed"]
    assert "scripts/search.py" in policy["dormant_snapshot_only"]
    assert "cli/**" in policy["denied"]
    assert "persist" in policy["denied"]
    assert "auto_update" in policy["denied"]


def test_local_domain_and_stack_search_are_read_only() -> None:
    root = provider_module._provider_root()
    before = provider_module._provider_file_state(root)
    ux = search_domain(
        "enterprise dashboard information hierarchy accessibility",
        "ux",
        4,
    )
    react = search_stack(
        "Keep components small and focused",
        "react",
        4,
    )
    after = provider_module._provider_file_state(root)
    assert ux["mode"] == "READ_ONLY_LOCAL_SEARCH"
    assert ux["result"]["count"] >= 1
    assert react["mode"] == "READ_ONLY_LOCAL_STACK_SEARCH"
    assert react["result"]["count"] >= 1
    assert before == after


def test_full_design_reasoning_is_advisory_and_non_persistent() -> None:
    root = provider_module._provider_root()
    before = provider_module._provider_file_state(root)
    result = recommend_design_system(
        "enterprise AI agent operations command center RTL dashboard",
        project_name="PalWakf Agentic Console",
        variance=4,
        motion=2,
        density=6,
    )
    after = provider_module._provider_file_state(root)
    assert result["schema_id"] == "palwakf.ui_ux_design_intelligence.recommendation.v1"
    assert result["recommendation_authority"] == "ADVISORY_ONLY"
    assert result["automatic_source_write"] is False
    assert result["automatic_dependency_write"] is False
    assert result["automatic_palette_adoption"] is False
    assert result["automatic_typography_adoption"] is False
    assert result["persistence"] is None
    assert result["design_system"] is not None
    assert before == after


@pytest.mark.parametrize("domain", ["shell", "network", "installer", ""])
def test_non_admitted_domains_rejected(domain: str) -> None:
    with pytest.raises(ValueError, match="UI_UX_DOMAIN_NOT_ADMITTED"):
        search_domain("test", domain)


@pytest.mark.parametrize("stack", ["powershell", "bash", "npm", ""])
def test_non_admitted_stacks_rejected(stack: str) -> None:
    with pytest.raises(ValueError, match="UI_UX_STACK_NOT_ADMITTED"):
        search_stack("test", stack)


@pytest.mark.parametrize(
    ("name", "value"),
    [("VARIANCE", 0), ("VARIANCE", 11), ("MOTION", 0), ("DENSITY", 12)],
)
def test_design_dials_fail_closed_outside_range(name: str, value: int) -> None:
    kwargs = {"variance": 4, "motion": 2, "density": 6}
    kwargs[name.lower()] = value
    with pytest.raises(ValueError, match=f"UI_UX_{name}_OUT_OF_RANGE"):
        recommend_design_system("dashboard", **kwargs)


def test_public_design_api_does_not_expose_persistence_or_command_surface() -> None:
    signature = inspect.signature(recommend_design_system)
    assert "persist" not in signature.parameters
    assert "output_dir" not in signature.parameters
    assert "command" not in signature.parameters
    assert "executable" not in signature.parameters
    search_signature = inspect.signature(search_domain)
    assert "root" not in search_signature.parameters


def test_tampered_archive_hash_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    previous_root = provider_module._MATERIALIZED_PROVIDER_ROOT
    provider_module._MATERIALIZED_PROVIDER_ROOT = None
    monkeypatch.setattr(provider_module, "SNAPSHOT_ARCHIVE_SHA256", "0" * 64)
    try:
        with pytest.raises(
            ProviderIntegrityError,
            match="UI_UX_PROVIDER_ARCHIVE_HASH_MISMATCH",
        ):
            verify_provider_snapshot()
    finally:
        if previous_root is not None:
            provider_module._MATERIALIZED_PROVIDER_ROOT = previous_root


def test_materialized_snapshot_is_outside_project_tree() -> None:
    root = provider_module._provider_root()
    project_fragment = "agentic_p4_ui_ux_v4_mega_batch"
    assert project_fragment.lower() not in str(root).lower()
    assert root.is_dir()


def test_snapshot_manifest_contains_no_denied_runtime_paths() -> None:
    expected = provider_module._expected_entries()
    assert not any(path.startswith("cli/") for path in expected)
    assert not any(path.startswith(".claude/") for path in expected)
