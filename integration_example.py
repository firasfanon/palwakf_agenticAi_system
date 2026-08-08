"""Example only — add the two marked lines to the existing local FastAPI app entrypoint.

Do not create a second runtime. Mount this router inside the existing FastAPI application.
"""
from pathlib import Path
from fastapi import FastAPI
from command_center import mount_command_center

app = FastAPI()
PROJECT_ROOT = Path(__file__).resolve().parent

# Command Center V1: read-only only.
mount_command_center(
    app,
    project_root=PROJECT_ROOT,
    ui_prefix='/command-center',
    api_prefix='/api/v1/local-agents',
)
