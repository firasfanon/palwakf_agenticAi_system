from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SAFE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")


def validate_identifier(value: str, label: str) -> str:
    cleaned = str(value or "").strip().lower()
    if not cleaned or any(char not in SAFE_ID_CHARS for char in cleaned):
        raise ValueError(f"INVALID_{label.upper()}_IDENTIFIER")
    return cleaned


def package_policy_root() -> Path:
    return Path(__file__).resolve().parents[4] / "policy_packs"


def load_policy_pack(policy_root: Path, policy_pack_id: str) -> dict[str, Any]:
    policy_pack_id = validate_identifier(policy_pack_id, "policy_pack")
    manifest = (policy_root / policy_pack_id / "policy.json").resolve()
    root = policy_root.resolve()
    if root not in manifest.parents or not manifest.is_file():
        raise FileNotFoundError("POLICY_PACK_NOT_FOUND")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("policy_pack_id") != policy_pack_id:
        raise ValueError("POLICY_PACK_ID_MISMATCH")
    return data
