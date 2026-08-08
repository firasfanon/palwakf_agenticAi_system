from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from palwakf_local_agents.governed_capability_foundation.authz import (
    ActorPrincipal,
    LocalActorScopeRegistry,
    require_commercial_client_scope,
    require_workspace_scope,
)
from palwakf_local_agents.workspace_core.policy import validate_identifier


LEGACY_WRITE_AUTHORIZATION_CONTRACT = "LEGACY_WRITE_AUTHORIZATION_CLOSURE_V1"
CLIENT_SCOPE_HEADER = "X-Palwakf-Client-Id"


def _deny(status_code: int, code: str, **extra: Any) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, **extra})


def _actor_identifier(value: str) -> str:
    cleaned = str(value or "").strip().lower()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_.-")
    if not cleaned or any(char not in allowed for char in cleaned):
        _deny(400, "INVALID_DECLARED_ACTOR_IDENTIFIER")
    return cleaned


@dataclass(frozen=True)
class LegacyWriteAuthorizationContext:
    contract: str
    actor_id: str
    workspace_id: str
    action: str
    workspace_classification: str
    client_id: str | None


class LegacyWriteAuthorizer:
    """Single fail-closed write authorization boundary for legacy modules.

    The boundary is intentionally invoked before any store method. It validates the
    authenticated principal, workspace/action scope, declared actor identity, and
    commercial client context. Legacy modules that cannot persist client context are
    blocked for commercial workspaces rather than accepting an unauditable write.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def _workspace_manifest(self, workspace_id: str) -> dict[str, Any]:
        workspace_id = validate_identifier(workspace_id, "workspace")
        path = self.project_root / "workspaces" / workspace_id / "workspace_manifest.json"
        if not path.is_file():
            _deny(503, "WORKSPACE_MANIFEST_NOT_CONFIGURED", workspace_id=workspace_id)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            _deny(503, "WORKSPACE_MANIFEST_INVALID", workspace_id=workspace_id)
        if document.get("workspace_id") != workspace_id:
            _deny(503, "WORKSPACE_MANIFEST_ID_MISMATCH", workspace_id=workspace_id)
        classification = str(document.get("classification") or "").strip().lower()
        if classification not in {"government", "personal", "research", "commercial"}:
            _deny(503, "WORKSPACE_CLASSIFICATION_INVALID", workspace_id=workspace_id)
        return document

    def authorize(
        self,
        request: Request,
        actor: ActorPrincipal,
        workspace_id: str,
        action: str,
        *,
        declared_actor_id: str | None = None,
        client_id: str | None = None,
        commercial_persistence_supported: bool,
    ) -> LegacyWriteAuthorizationContext:
        workspace_id = validate_identifier(workspace_id, "workspace")
        action = str(action or "").strip().lower()
        require_workspace_scope(actor, workspace_id, action)

        if declared_actor_id is not None and _actor_identifier(declared_actor_id) != actor.actor_id:
            _deny(
                403,
                "DECLARED_ACTOR_MISMATCH",
                actor_id=actor.actor_id,
                declared_actor_id=_actor_identifier(declared_actor_id),
            )

        manifest = self._workspace_manifest(workspace_id)
        classification = str(manifest["classification"]).strip().lower()
        header_client = request.headers.get(CLIENT_SCOPE_HEADER)
        payload_client = str(client_id).strip() if client_id is not None else None
        header_client = str(header_client).strip() if header_client is not None else None
        if payload_client and header_client and payload_client != header_client:
            _deny(400, "CLIENT_CONTEXT_CONFLICT")
        effective_client = payload_client or header_client

        if classification == "commercial":
            if not effective_client:
                _deny(400, "COMMERCIAL_CLIENT_CONTEXT_REQUIRED", workspace_id=workspace_id)
            effective_client = validate_identifier(effective_client, "client")
            require_commercial_client_scope(actor, effective_client)
            if not commercial_persistence_supported:
                _deny(
                    403,
                    "COMMERCIAL_LEGACY_WRITE_CONTEXT_NOT_SUPPORTED",
                    workspace_id=workspace_id,
                    client_id=effective_client,
                )
        elif effective_client:
            _deny(400, "CLIENT_CONTEXT_NOT_ALLOWED_OUTSIDE_COMMERCIAL_WORKSPACE", workspace_id=workspace_id)

        return LegacyWriteAuthorizationContext(
            contract=LEGACY_WRITE_AUTHORIZATION_CONTRACT,
            actor_id=actor.actor_id,
            workspace_id=workspace_id,
            action=action,
            workspace_classification=classification,
            client_id=effective_client,
        )


def install_legacy_write_authorization_boundary(app: FastAPI, project_root: Path) -> None:
    """Install shared actor registry and write authorizer exactly once per FastAPI app."""
    if getattr(app.state, "governed_capability_authz_registry", None) is None:
        app.state.governed_capability_authz_registry = LocalActorScopeRegistry(project_root)
    if getattr(app.state, "legacy_write_authorizer", None) is None:
        app.state.legacy_write_authorizer = LegacyWriteAuthorizer(project_root)
