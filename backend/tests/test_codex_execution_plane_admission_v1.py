from __future__ import annotations

import json
from pathlib import Path


def test_codex_execution_plane_config_contract():
    data = json.loads(Path("config/palwakf_codex_execution_plane_v1.json").read_text(encoding="utf-8"))
    assert data["role"] == "PRIVILEGED_ENGINEERING_BOOTSTRAP_RECOVERY_PLANE"
    assert data["execution_mode"] == "SELF_HOSTED_CODEX_EXEC_SERVER"
    assert data["credentials"]["require_distinct_keys"] is True
    assert data["credentials"]["allow_secret_in_git"] is False
    assert data["retirement_gate"]["palwakf_remote_mcp"] == "RETAIN"
    assert data["retirement_gate"]["remote_desktop_commander"] == "BREAK_GLASS_ONLY"


def test_codex_bootstrap_is_secret_free_and_exec_server_specific():
    source = Path("scripts/Bootstrap-PalWakfCodexExecutionPlaneV1.ps1").read_text(encoding="utf-8")
    assert "@openai/codex@alpha" in source
    assert "exec-server --help" in source
    assert "CODEX_EXEC_SERVER=AVAILABLE" in source
    assert "credential_material_provisioned = $false" in source
    assert "OPENAI_API_KEY=" not in source
    assert "CODEX_API_KEY=" not in source
    assert "sk-" not in source


def test_admission_doc_preserves_separation_of_duties():
    source = Path("docs/PALWAKF_CODEX_EXECUTION_PLANE_ADMISSION_V1.md").read_text(encoding="utf-8")
    assert "PALWAKF_LOCAL_EXECUTOR remains the governed operational execution plane" in source
    assert "PALWAKF_REMOTE_MCP remains the secure bounded observability" in source
    assert "REMOTE_DESKTOP_COMMANDER remains break-glass only" in source
    assert "Render Responses relay and Task Scheduler relay remain available until" in source
