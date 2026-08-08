from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv('LOCAL_AGENT_HOST', '127.0.0.1')
    port: int = int(os.getenv('LOCAL_AGENT_PORT', '8765'))
    ollama_base_url: str = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
    allow_agent_execution: bool = _truthy(os.getenv('ALLOW_AGENT_EXECUTION', 'false'))
    allow_platform_mutation: bool = _truthy(os.getenv('ALLOW_PLATFORM_MUTATION', 'false'))
    allow_database_access: bool = _truthy(os.getenv('ALLOW_DATABASE_ACCESS', 'false'))

    def safety_ok(self) -> bool:
        return not self.allow_agent_execution and not self.allow_platform_mutation and not self.allow_database_access


settings = Settings()
