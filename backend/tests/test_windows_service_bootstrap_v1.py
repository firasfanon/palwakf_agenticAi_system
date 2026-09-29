from __future__ import annotations

import ast
from pathlib import Path


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
