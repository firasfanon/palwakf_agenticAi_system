from pathlib import Path

import pytest
from fastapi import HTTPException

from palwakf_local_agents.governed_capability_foundation.authz import ActorPrincipal, LocalActorScopeRegistry, require_commercial_client_scope, require_workspace_scope
from palwakf_local_agents.governed_capability_foundation.tools import deterministic_tool


def test_deterministic_summary_has_no_model_execution():
    result = deterministic_tool("summarize", "First sentence. Second sentence. Third sentence.")
    assert result["model_execution"] == "NONE"
    assert result["summary_points"] == ["First sentence", "Second sentence", "Third sentence"]


def test_cross_workspace_scope_is_denied():
    actor = ActorPrincipal("firas_fanon", frozenset({"research_learning"}), frozenset({"read"}), frozenset())
    with pytest.raises(HTTPException) as exc:
        require_workspace_scope(actor, "commercial_projects", "read")
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "WORKSPACE_SCOPE_DENIED"


def test_commercial_client_scope_is_denied_when_not_assigned():
    actor = ActorPrincipal("firas_fanon", frozenset({"commercial_projects"}), frozenset({"write"}), frozenset({"client_a"}))
    with pytest.raises(HTTPException) as exc:
        require_commercial_client_scope(actor, "client_b")
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "COMMERCIAL_CLIENT_SCOPE_DENIED"


def test_empty_registry_denies_authentication(tmp_path: Path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "local_actor_scope_registry_v1.json").write_text('{"contract":"LOCAL_ACTOR_SCOPE_REGISTRY_V1","default_access":"DENY","actors":[]}', encoding="utf-8")
    registry = LocalActorScopeRegistry(tmp_path)
    with pytest.raises(HTTPException) as exc:
        registry.authenticate_bearer("Bearer not-configured")
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "ACTOR_AUTHENTICATION_FAILED"
