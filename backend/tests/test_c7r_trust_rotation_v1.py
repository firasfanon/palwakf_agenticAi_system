from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from palwakf_local_agents.outbound_worker_v1 import WorkerConfigV1


def _config(path: Path | None) -> WorkerConfigV1:
    return WorkerConfigV1.model_validate(
        {
            "executor": {
                "executor_id": "DESKTOP-S5A0JSB",
                "repository_id": "firasfanon/palwakf_agenticAi_system",
                "allowed_roots": [r"C:\repo"],
                "state_dir": r"C:\state",
            },
            "transport": {
                "repository": "firasfanon/palwakf_agenticAi_system",
                "task_label": "question",
                "token_env_var": "PALWAKF_GITHUB_TOKEN",
                "token_protected_path": None,
            },
            "authority_public_keys_b64": {
                "acceptance-r11": base64.b64encode(b"a" * 32).decode("ascii"),
            },
            "authority_public_keys_path": str(path) if path is not None else None,
        }
    )


def test_external_public_trust_store_merges_without_replacing_existing_key(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authority-keys.json"
    rotated = base64.b64encode(b"b" * 32).decode("ascii")
    path.write_text(
        json.dumps({"workspace-c7r-v1": rotated}),
        encoding="utf-8",
    )

    keys = _config(path).effective_authority_public_keys()

    assert set(keys) == {"acceptance-r11", "workspace-c7r-v1"}
    assert keys["workspace-c7r-v1"] == rotated


def test_external_public_trust_store_rejects_key_id_conflict(tmp_path: Path) -> None:
    path = tmp_path / "authority-keys.json"
    path.write_text(
        json.dumps(
            {"acceptance-r11": base64.b64encode(b"z" * 32).decode("ascii")}
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="AUTHORITY_PUBLIC_KEY_CONFLICT"):
        _config(path).effective_authority_public_keys()


def test_missing_external_public_trust_store_preserves_embedded_acceptance_key(
    tmp_path: Path,
) -> None:
    keys = _config(tmp_path / "missing.json").effective_authority_public_keys()

    assert list(keys) == ["acceptance-r11"]


def test_external_public_trust_store_can_be_the_sole_runtime_root(tmp_path: Path) -> None:
    path = tmp_path / "authority-keys.json"
    durable = base64.b64encode(b"d" * 32).decode("ascii")
    path.write_text(
        json.dumps({"workspace-c7r-v1": durable}),
        encoding="utf-8",
    )
    config = _config(path).model_copy(update={"authority_public_keys_b64": {}})

    keys = config.effective_authority_public_keys()

    assert keys == {"workspace-c7r-v1": durable}


def test_empty_authority_root_fails_closed(tmp_path: Path) -> None:
    config = _config(None).model_copy(update={"authority_public_keys_b64": {}})

    with pytest.raises(RuntimeError, match="AUTHORITY_PUBLIC_KEY_STORE_EMPTY"):
        config.effective_authority_public_keys()
