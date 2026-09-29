from __future__ import annotations

import ast
import base64
from pathlib import Path

import pytest

from palwakf_local_agents.windows_protected_secret_v1 import (
    ProtectedSecretError,
    _read_protected_payload_bytes,
)


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
    source = Path("scripts/Bootstrap-PalWakfOutboundLocalExecutorV1.ps1").read_text(encoding="utf-8")
    assert "WINDOWS_SERVICE_NOT_RUNNING" in source
    assert "Start-Service -Name PalWakfOutboundLocalExecutorV1 -ErrorAction Stop" in source


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
