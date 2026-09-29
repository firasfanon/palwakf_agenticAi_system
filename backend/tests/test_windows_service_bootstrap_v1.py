from __future__ import annotations

import ast
import base64
from pathlib import Path

import pytest

from palwakf_local_agents.windows_protected_secret_v1 import (
    ProtectedSecretError,
    _read_protected_payload_bytes,
)


def _bootstrap_source() -> str:
    return Path("scripts/Bootstrap-PalWakfOutboundLocalExecutorV1.ps1").read_text(encoding="utf-8")


def test_windows_service_class_is_module_level():
    source = Path("backend/src/palwakf_local_agents/windows_service_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    module_level_classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    module_level_if_classes = {
        child.name
        for node in tree.body
        if isinstance(node, ast.If)
        for child in node.body
        if isinstance(child, ast.ClassDef)
    }
    assert "PalWakfOutboundExecutorService" in (module_level_classes | module_level_if_classes)


def test_bootstrap_requires_running_service():
    source = _bootstrap_source()
    assert "WINDOWS_SERVICE_NOT_RUNNING" in source
    assert "Start-Service -Name $svcName -ErrorAction Stop" in source


def test_bootstrap_uses_machine_global_pywin32_service_host():
    source = _bootstrap_source()
    assert "pywin32_postinstall.exe" in source
    assert "& $postinstall -install -silent" in source
    assert "-m pywin32_postinstall" not in source
    assert ".venv-outbound-executor-v1" not in source
    assert "MACHINE_PYTHON_MUST_NOT_BE_USER_SCOPED" in source
    assert "PYTHONSERVICE_EXE_NOT_MACHINE_GLOBAL" in source
    assert "SERVICE_IMAGE_PATH_NOT_MACHINE_GLOBAL" in source
    assert "-match '^C:\\Users\\'" not in source
    assert "-match 'C:\\Users\\'" not in source
    assert "-like 'C:\\Users\\*'" in source
    assert "$serviceExeOutput = @(" in source
    assert "$serviceExeCandidates = @(" in source
    assert "Test-Path -LiteralPath $_ -PathType Leaf" in source
    assert "$serviceExe = $serviceExeCandidates[-1]" in source
    assert "palwakf_outbound_executor_v1.acceptance.json" in source
    assert "Copy-Item -LiteralPath $authoritativeConfig -Destination $config -Force" in source
    assert "EXECUTOR_CONFIG_SYNC_HASH_MISMATCH" in source
    assert "ConfigSync = 'PASS'" in source


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_protected_secret_payload_accepts_utf8_with_or_without_bom(tmp_path, encoding):
    payload = b"palwakf-protected-secret-bytes"
    path = tmp_path / "github_token.dpapi"
    path.write_text(base64.b64encode(payload).decode("ascii"), encoding=encoding)
    assert _read_protected_payload_bytes(str(path)) == payload


def test_protected_secret_payload_rejects_non_base64(tmp_path):
    path = tmp_path / "github_token.dpapi"
    path.write_text("not-base64-***", encoding="utf-8")
    with pytest.raises(ProtectedSecretError, match="WINDOWS_PROTECTED_SECRET_ENCODING_INVALID"):
        _read_protected_payload_bytes(str(path))
