from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def actor_record(
    actor_id: str,
    token: str,
    workspace_scopes: list[str],
    allowed_actions: list[str],
    commercial_client_scopes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "token_sha256": _sha256(token),
        "workspace_scopes": workspace_scopes,
        "allowed_actions": allowed_actions,
        "commercial_client_scopes": commercial_client_scopes or [],
    }


def seed_authorized_test_project(root: Path) -> Path:
    """Create a disposable local-only project with explicit test actors.

    This helper is test-only. It never provisions or mutates the repository's
    real actor registry, workspaces, SQLite files, or model configuration.
    """
    shutil.copytree(PROJECT_ROOT / "policy_packs", root / "policy_packs")
    shutil.copytree(
        PROJECT_ROOT / "workspaces",
        root / "workspaces",
        ignore=shutil.ignore_patterns("*.sqlite", "*.sqlite-*", "*.sqlite3", "*.sqlite3-*"),
    )
    config = root / "config"
    config.mkdir(parents=True, exist_ok=True)
    actors = [
        actor_record(
            "test_operator",
            "governed-test-operator-token",
            ["palwakf_government"],
            ["read", "write", "review", "tool"],
        ),
        actor_record(
            "local.operator",
            "local-agent-test-operator-token",
            ["palwakf_government"],
            ["read", "write", "pilot"],
        ),
        actor_record(
            "foundation.operator",
            "foundation-test-operator-token",
            ["research_learning"],
            ["read", "write", "tool"],
        ),
    ]
    (config / "local_actor_scope_registry_v1.json").write_text(
        json.dumps(
            {
                "contract": "LOCAL_ACTOR_SCOPE_REGISTRY_V1",
                "version": "TEST_ONLY_V1",
                "default_access": "DENY",
                "actors": actors,
                "test_only": True,
                "production_provisioning": "FORBIDDEN",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for filename in ("local_agent_model_pilot_v1.json", "controlled_first_prompt_pilot_v1.json"):
        shutil.copy2(PROJECT_ROOT / "config" / filename, config / filename)
    return root


@pytest.fixture
def authorized_project(tmp_path: Path) -> Path:
    return seed_authorized_test_project(tmp_path)


@pytest.fixture
def governed_headers() -> dict[str, str]:
    return {"Authorization": "Bearer governed-test-operator-token"}


@pytest.fixture
def local_agent_headers() -> dict[str, str]:
    return {"Authorization": "Bearer local-agent-test-operator-token"}


@pytest.fixture
def foundation_headers() -> dict[str, str]:
    return {"Authorization": "Bearer foundation-test-operator-token"}
