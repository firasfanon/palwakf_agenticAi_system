from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from palwakf_local_agents.workspace_core.policy import validate_identifier


ACTOR_SCOPE_REGISTRY_CONTRACT = "LOCAL_ACTOR_SCOPE_REGISTRY_V1"


def _deny(status_code: int, code: str, **extra: Any) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, **extra})


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def validate_actor_identifier(value: str) -> str:
    """Actor IDs follow the documented local contract: letters, digits, _, -, and ."""
    cleaned = str(value or "").strip().lower()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_.-")
    if not cleaned or any(char not in allowed for char in cleaned):
        raise ValueError("INVALID_ACTOR_IDENTIFIER")
    return cleaned


@dataclass(frozen=True)
class ActorPrincipal:
    actor_id: str
    workspace_scopes: frozenset[str]
    allowed_actions: frozenset[str]
    commercial_client_scopes: frozenset[str]


class LocalActorScopeRegistry:
    def __init__(self, project_root: Path) -> None:
        self.path = project_root / "config" / "local_actor_scope_registry_v1.json"

    def _document(self) -> dict[str, Any]:
        if not self.path.is_file():
            _deny(503, "ACTOR_SCOPE_REGISTRY_NOT_CONFIGURED")
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            _deny(503, "ACTOR_SCOPE_REGISTRY_INVALID")
            raise AssertionError("unreachable") from error
        if document.get("contract") != ACTOR_SCOPE_REGISTRY_CONTRACT:
            _deny(503, "ACTOR_SCOPE_REGISTRY_CONTRACT_MISMATCH")
        if document.get("default_access") != "DENY":
            _deny(503, "ACTOR_SCOPE_REGISTRY_DEFAULT_NOT_DENY")
        actors = document.get("actors")
        if not isinstance(actors, list):
            _deny(503, "ACTOR_SCOPE_REGISTRY_ACTORS_INVALID")
        return document

    def authenticate_bearer(self, authorization: str | None) -> ActorPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            _deny(401, "AUTHENTICATED_ACTOR_REQUIRED")
        token = authorization[7:].strip()
        if not token:
            _deny(401, "AUTHENTICATED_ACTOR_REQUIRED")
        token_hash = _token_hash(token)
        for actor in self._document()["actors"]:
            if actor.get("token_sha256") != token_hash:
                continue
            try:
                actor_id = validate_actor_identifier(actor.get("actor_id", ""))
                workspaces = frozenset(validate_identifier(item, "workspace") for item in actor.get("workspace_scopes", []))
                actions = frozenset(str(item).strip().lower() for item in actor.get("allowed_actions", []))
                clients = frozenset(validate_identifier(item, "client") for item in actor.get("commercial_client_scopes", []))
            except ValueError:
                _deny(403, "ACTOR_SCOPE_CONFIGURATION_INVALID")
            if not workspaces or not actions:
                _deny(403, "ACTOR_SCOPE_CONFIGURATION_INVALID", actor_id=actor_id)
            return ActorPrincipal(actor_id, workspaces, actions, clients)
        _deny(401, "ACTOR_AUTHENTICATION_FAILED")
        raise AssertionError("unreachable")


def authenticated_actor(request: Request) -> ActorPrincipal:
    registry = getattr(request.app.state, "governed_capability_authz_registry", None)
    if registry is None:
        _deny(503, "AUTHORIZATION_BOUNDARY_NOT_INITIALIZED")
    return registry.authenticate_bearer(request.headers.get("Authorization"))


def require_workspace_scope(actor: ActorPrincipal, workspace_id: str, action: str) -> None:
    workspace_id = validate_identifier(workspace_id, "workspace")
    action = str(action).strip().lower()
    if workspace_id not in actor.workspace_scopes:
        _deny(403, "WORKSPACE_SCOPE_DENIED", workspace_id=workspace_id, actor_id=actor.actor_id)
    if action not in actor.allowed_actions:
        _deny(403, "WORKSPACE_ACTION_DENIED", workspace_id=workspace_id, action=action, actor_id=actor.actor_id)


def require_commercial_client_scope(actor: ActorPrincipal, client_id: str) -> str:
    client_id = validate_identifier(client_id, "client")
    if client_id not in actor.commercial_client_scopes:
        _deny(403, "COMMERCIAL_CLIENT_SCOPE_DENIED", client_id=client_id, actor_id=actor.actor_id)
    return client_id
