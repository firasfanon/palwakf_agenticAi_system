from __future__ import annotations

from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / 'agents' / 'registry.yaml'


def load_registry() -> dict:
    with REGISTRY_PATH.open('r', encoding='utf-8') as stream:
        return yaml.safe_load(stream) or {}


def list_agents() -> list[dict]:
    registry = load_registry()
    return list(registry.get('roles', []))
