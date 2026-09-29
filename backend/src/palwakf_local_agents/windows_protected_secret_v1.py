from __future__ import annotations

import base64
import os
from pathlib import Path


class ProtectedSecretError(RuntimeError):
    pass


def read_windows_protected_text(path: str) -> str:
    if os.name != "nt":
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_REQUIRES_WINDOWS")
    target = Path(path)
    if not target.is_file():
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_NOT_FOUND")
    try:
        import win32crypt
    except ImportError as exc:
        raise ProtectedSecretError("PYWIN32_REQUIRED_FOR_PROTECTED_SECRET") from exc
    try:
        encrypted = base64.b64decode(target.read_text(encoding="utf-8").strip(), validate=True)
        _, plain = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        value = plain.decode("utf-8")
    except Exception as exc:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_DECRYPT_FAILED") from exc
    if not value:
        raise ProtectedSecretError("WINDOWS_PROTECTED_SECRET_EMPTY")
    return value
