from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityContextV1,
    CapabilityError,
)
from palwakf_local_agents.windows_protected_secret_v1 import (
    ProtectedSecretError,
    read_windows_protected_text,
)


def _config() -> tuple[str, str | None, str | None, str, tuple[str, ...]]:
    executable = os.environ.get("PALWAKF_RCLONE_EXECUTABLE", "").strip()
    config = os.environ.get("PALWAKF_RCLONE_CONFIG", "").strip() or None
    protected = (
        os.environ.get("PALWAKF_RCLONE_CONFIG_PROTECTED", "").strip() or None
    )
    remote = os.environ.get("PALWAKF_DRIVE_REMOTE_NAME", "").strip()
    prefixes_raw = os.environ.get("PALWAKF_DRIVE_ALLOWED_PREFIXES", "")
    prefixes = tuple(
        p.strip().replace("\\", "/").strip("/")
        for p in prefixes_raw.split(";")
        if p.strip()
    )
    if (
        not executable
        or not remote
        or not prefixes
        or bool(config) == bool(protected)
    ):
        raise CapabilityError("WORKSPACE_DRIVE_NOT_CONFIGURED")
    return executable, config, protected, remote, prefixes


def _normalized(path: str) -> str:
    value = path.replace("\\", "/").strip("/")
    if not value or ".." in value.split("/"):
        raise CapabilityError("WORKSPACE_DRIVE_PATH_INVALID")
    return value


def _authorize_path(
    ctx: CapabilityContextV1,
    path: str,
    prefixes: tuple[str, ...],
) -> str:
    value = _normalized(path)
    if not any(value == prefix or value.startswith(prefix + "/") for prefix in prefixes):
        raise CapabilityError("WORKSPACE_DRIVE_PATH_OUTSIDE_ALLOWLIST")
    scoped = False
    for raw in ctx.scope_paths:
        if not raw.startswith("drive://"):
            continue
        scope = _normalized(raw[len("drive://") :])
        if value == scope or value.startswith(scope + "/"):
            scoped = True
            break
    if not scoped:
        raise CapabilityError("WORKSPACE_DRIVE_SCOPE_WIDENING_DENIED")
    return value


def _rclone(
    executable: str,
    config_path: str | None,
    protected_path: str | None,
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[bytes]:
    def invoke(path: str) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                [executable, "--config", path, *args],
                input=input_bytes,
                shell=False,
                capture_output=True,
                text=False,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise CapabilityError(
                f"WORKSPACE_DRIVE_EXECUTION_FAILED:{type(exc).__name__}"
            ) from exc

    if config_path:
        return invoke(config_path)
    try:
        config_text = read_windows_protected_text(str(protected_path))
    except ProtectedSecretError as exc:
        raise CapabilityError("WORKSPACE_DRIVE_PROTECTED_CONFIG_UNAVAILABLE") from exc
    with tempfile.TemporaryDirectory(prefix="palwakf-drive-config-") as temp_dir:
        temp = Path(temp_dir) / "rclone.conf"
        temp.write_text(config_text, encoding="utf-8")
        return invoke(str(temp))


def workspace_drive_read(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    executable, config, protected, remote, prefixes = _config()
    path = _authorize_path(ctx, str(args.get("drive_path", "")), prefixes)
    max_bytes = int(args.get("max_bytes", min(65536, ctx.max_output_bytes)))
    if max_bytes < 1 or max_bytes > ctx.max_output_bytes:
        raise CapabilityError("WORKSPACE_DRIVE_MAX_BYTES_INVALID")
    result = _rclone(
        executable,
        config,
        protected,
        [
            "cat",
            f"{remote}:{path}",
            "--count",
            str(max_bytes + 1),
        ],
    )
    if result.returncode != 0:
        raise CapabilityError("WORKSPACE_DRIVE_READ_FAILED")
    data = result.stdout
    if len(data) > max_bytes:
        raise CapabilityError("WORKSPACE_DRIVE_READ_TOO_LARGE")
    return {
        "drive_path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "content": data.decode("utf-8", errors="replace"),
    }


def workspace_drive_write_bounded(
    ctx: CapabilityContextV1,
    args: Mapping[str, Any],
) -> Mapping[str, Any]:
    executable, config, protected, remote, prefixes = _config()
    path = _authorize_path(ctx, str(args.get("drive_path", "")), prefixes)
    content = args.get("content")
    if not isinstance(content, str):
        raise CapabilityError("WORKSPACE_DRIVE_CONTENT_REQUIRED")
    data = content.encode("utf-8")
    if len(data) > ctx.max_output_bytes:
        raise CapabilityError("WORKSPACE_DRIVE_WRITE_TOO_LARGE")

    expected = args.get("expected_sha256")
    create_only = args.get("create_only") is True
    if create_only and expected is not None:
        raise CapabilityError("WORKSPACE_DRIVE_PRECONDITION_CONFLICT")
    if not create_only and expected is None:
        raise CapabilityError("WORKSPACE_DRIVE_REVISION_PRECONDITION_REQUIRED")

    stat = _rclone(
        executable,
        config,
        protected,
        ["lsjson",
            f"{remote}:{path}",
            "--stat",
        ]
    )
    exists = stat.returncode == 0
    if create_only:
        if exists:
            raise CapabilityError("WORKSPACE_DRIVE_CREATE_TARGET_EXISTS")
    else:
        if not exists:
            raise CapabilityError("WORKSPACE_DRIVE_UPDATE_TARGET_MISSING")
        expected = str(expected).lower()
        current = workspace_drive_read(
            ctx,
            {"drive_path": path, "max_bytes": ctx.max_output_bytes},
        )
        if current["sha256"] != expected:
            raise CapabilityError("WORKSPACE_DRIVE_REVISION_PRECONDITION_FAILED")

    with tempfile.TemporaryDirectory(prefix="palwakf-drive-write-") as temp_dir:
        local = Path(temp_dir) / "payload"
        local.write_bytes(data)
        result = _rclone(
            executable,
            config,
            protected,
            ["copyto",
                str(local),
                f"{remote}:{path}",
            ]
        )
    if result.returncode != 0:
        raise CapabilityError("WORKSPACE_DRIVE_WRITE_FAILED")
    return {
        "drive_path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "revision_precondition_enforced": expected is not None,
    }
