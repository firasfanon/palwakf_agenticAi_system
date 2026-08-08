from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SafeFile:
    kind: str
    relative_path: str
    modified_at: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


SAFETY_POSTURE = {
    "MODEL_EXECUTION": "NONE",
    "PILOT_EXECUTION": "NOT_EXECUTED",
    "PLATFORM_MUTATION": "NONE",
    "DATABASE_ACCESS": "NONE",
    "GIT_WRITE": "NONE",
    "DEPLOYMENT": "NONE",
    "SECRETS_ACCESS": "NONE",
    "MEMORY_WRITE": "NONE",
}
