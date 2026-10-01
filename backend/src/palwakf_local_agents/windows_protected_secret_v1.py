from __future__ import annotations

import base64
import os
from pathlib import Path


class ProtectedSecretError(RuntimeError):
    pass


def _read_protected_payload_bytes(path: str) -> bytes:
    target = Path(path)
    if not target.is_file():
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_NOT_FOUND")
    try:
        encoded = target.read_text(encoding="utf-8-sig").strip()
        return base64.b64decode(encoded, validate=True)
    except ProtectedSecretError:
        raise
    except Exception as exc:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_ENCODING_INVALID") from exc


def read_windows_protected_text(path: str) -> str:
    if os.name != "nt":
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_REQUIRES_WINDOWS")
    try:
        import win32crypt
    except ImportError as exc:
        raise ProtectedSecretError("PYWIN32_REQUIRED_FOR_PROTECTED_SECRET") from exc
    try:
        encrypted = _read_protected_payload_bytes(path)
        _, plain = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        value = plain.decode("utf-8")
    except ProtectedSecretError:
        raise
    except Exception as exc:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_DECRYPT_FAILED") from exc
    if not value:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_EMPTY")
    return value


def write_windows_protected_text(
    path: str,
    value: str,
    *,
    machine_scope: bool = False,
) -> None:
    if os.name != "nt":
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_REQUIRES_WINDOWS")
    if not value:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_EMPTY")
    try:
        import win32crypt
    except ImportError as exc:
        raise ProtectedSecretError("PYWIN32_REQUIRED_FOR_PROTECTED_SECRET") from exc
    try:
        flags = 0x4 if machine_scope else 0
        encrypted = win32crypt.CryptProtectData(
            value.encode("utf-8"),
            "PalWakf protected secret",
            None,
            None,
            None,
            flags,
        )
        encoded = base64.b64encode(encrypted).decode("ascii")
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(encoded, encoding="utf-8")
        os.replace(temp, target)
    except ProtectedSecretError:
        raise
    except Exception as exc:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_ENCRYPT_FAILED") from exc
