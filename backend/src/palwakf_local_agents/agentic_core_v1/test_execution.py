from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

from .contracts import RunRequest

_IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
_SAFE_ENV_KEYS = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PYTHONPATH"}


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest(root: Path) -> str:
    records: list[tuple[str, int, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in _IGNORED_PARTS for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        records.append((relative, len(data), _sha256(data)))
    return _sha256(json.dumps(records, separators=(",", ":")).encode())


def _selector_path(root: Path, selector: str) -> str:
    file_part = selector.split("::", 1)[0].replace("\\", "/")
    pure = PurePosixPath(file_part)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", "..", ".git"} for part in pure.parts)
        or not file_part.endswith(".py")
    ):
        raise RuntimeError("CONTROLLED_TEST_SELECTOR_INVALID")
    if not (file_part.startswith("tests/") or file_part.startswith("backend/tests/")):
        raise RuntimeError("CONTROLLED_TEST_SELECTOR_SCOPE_DENIED")
    candidate = root.joinpath(*pure.parts)
    if not candidate.is_file():
        raise RuntimeError("CONTROLLED_TEST_SELECTOR_NOT_FOUND")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as error:
        raise RuntimeError("CONTROLLED_TEST_SELECTOR_ESCAPE") from error
    return selector.replace("\\", "/")


def _sanitized_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key in _SAFE_ENV_KEYS}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["NO_PROXY"] = "*"
    env["HTTP_PROXY"] = ""
    env["HTTPS_PROXY"] = ""
    env["ALL_PROXY"] = ""
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def run_controlled_tests(
    *, project_root: Path, request: RunRequest
) -> dict[str, object]:
    spec = request.test_spec
    if spec is None:
        raise RuntimeError("CONTROLLED_TEST_SPEC_REQUIRED")

    root = project_root.resolve()
    if (root / ".git").exists():
        raise RuntimeError("CONTROLLED_TEST_DISPOSABLE_COPY_REQUIRED")
    selectors = [_selector_path(root, item) for item in spec.selectors]
    before_manifest = _manifest(root)
    argv = [sys.executable, "-m", "pytest", "-q", *selectors]
    run = subprocess.run(
        argv,
        cwd=str(root),
        env=_sanitized_env(),
        capture_output=True,
        text=True,
        timeout=spec.timeout_seconds,
        shell=False,
        check=False,
    )
    after_manifest = _manifest(root)
    source_unchanged = before_manifest == after_manifest
    successful = run.returncode == spec.expected_exit_code and source_unchanged
    stdout = run.stdout or ""
    stderr = run.stderr or ""
    return {
        "provider_id": request.provider_id.value,
        "successful": successful,
        "action_type": "CONTROLLED_PYTEST_EXECUTION",
        "test_plan": {
            "plan_id": spec.plan_id,
            "selectors": selectors,
            "runner": "PYTHON_MODULE_PYTEST",
            "shell": False,
        },
        "tests": [
            {
                "exit_code": run.returncode,
                "expected_exit_code": spec.expected_exit_code,
                "stdout_sha256": _sha256(stdout.encode("utf-8")),
                "stderr_sha256": _sha256(stderr.encode("utf-8")),
                "stdout_excerpt": stdout[-4000:],
                "stderr_excerpt": stderr[-2000:],
                "result": "PASS" if successful else "FAIL",
            }
        ],
        "observations": [
            {
                "workspace_kind": "DISPOSABLE_COPY",
                "source_unchanged": source_unchanged,
                "network_environment": "PROXY_DISABLED_NO_OS_SANDBOX_CLAIM",
                "git_mutation": "NONE",
                "database": "DENIED",
                "model_inference": "NONE",
            }
        ],
        "errors": (
            []
            if successful
            else [
                {
                    "code": (
                        "CONTROLLED_TEST_SOURCE_MUTATION_DETECTED"
                        if not source_unchanged
                        else "CONTROLLED_TEST_EXIT_MISMATCH"
                    )
                }
            ]
        ),
        "changed_files": [],
        "evidence": [
            {
                "type": "CONTROLLED_TEST_EXECUTION_RECEIPT",
                "plan_id": spec.plan_id,
                "before_manifest_sha256": before_manifest,
                "after_manifest_sha256": after_manifest,
            }
        ],
        "process_success": run.returncode == spec.expected_exit_code,
        "policy_success": source_unchanged,
        "tool_execution_success": True,
        "objective_success": successful,
        "postcondition_success": source_unchanged,
        "tool_call_observed": True,
    }
