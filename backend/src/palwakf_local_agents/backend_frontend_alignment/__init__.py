from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI

from .router import build_router


def mount_backend_frontend_alignment(app: FastAPI, *, project_root: Path) -> None:
    app.include_router(build_router(project_root=project_root))
