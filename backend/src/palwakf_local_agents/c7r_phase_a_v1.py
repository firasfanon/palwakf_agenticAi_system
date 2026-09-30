from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import queue
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Mapping

import jwt
from jwt import PyJWKClient

from palwakf_local_agents.windows_protected_secret_v1 import (
    ProtectedSecretError,
    read_windows_protected_text,
    write_windows_protected_text,
)

AUTHORIZATION_ENDPOINT = "https://auth.openai.com/api/accounts/authorize"
TOKEN_ENDPOINT = "https://auth.openai.com/api/accounts/oauth/token"
JWKS_URI = "https://auth.openai.com/.well-known/jwks.json"
ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPES = (
    "openid",
    "profile",
    "email",
    "offline_access",
    "resource.invoke",
    "chatgpt.tokens.use.direct",
)
AGENT_NAME = "PalWakf"
CODEX_VERSION_PIN = "0.159.1"
WINDOWS_X86_64_SHA256 = "1203922d910426522182b35a52402085d0955101bb585a87bd7c88110d8d68d8"
SYNTHETIC_PROMPT = "Reply with exactly PALWAKF_C7R_PHASE_A_OK"
SYNTHETIC_EXPECTED = "PALWAKF_C7R_PHASE_A_OK"


class C7RPhaseAError(RuntimeError):
    pass


def _state_root() -> Path:
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    return Path(program_data) / "PalWakf" / "c7r_phase_a_v1"


def _paths() -> dict[str, Path]:
    root = _state_root()
    return {
        "root": root,
        "host_id": root / "host-id.txt",
        "credentials": root / "credentials.dpapi",
        "pending": root / "oauth-pending.dpapi",
        "registration": root / "registration.json",
        "status": root / "status.json",
        "auth_url": root / "authorization-url.txt",
        "refresh_lock": root / "refresh.lock",
        "runtime_admission": root / "runtime-admission.json",
    }


def _safe_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(dict(value), ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    os.replace(temp, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise C7RPhaseAError("JSON_STATE_MUST_BE_OBJECT")
    return value


def _protected_read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(read_windows_protected_text(str(path)))
    except (ProtectedSecretError, json.JSONDecodeError) as exc:
        raise C7RPhaseAError("PROTECTED_STATE_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise C7RPhaseAError("PROTECTED_STATE_MUST_BE_OBJECT")
    return value


def _protected_write_json(path: Path, value: Mapping[str, Any]) -> None:
    try:
        write_windows_protected_text(
            str(path),
            json.dumps(dict(value), ensure_ascii=False, sort_keys=True),
        )
    except ProtectedSecretError as exc:
        raise C7RPhaseAError("PROTECTED_STATE_WRITE_FAILED") from exc


def _stable_host_id() -> str:
    path = _paths()["host_id"]
    if path.is_file():
        value = path.read_text(encoding="utf-8").strip()
        if value.startswith("urn:uuid:"):
            return value
        raise C7RPhaseAError("HOST_ID_INVALID")
    value = f"urn:uuid:{uuid.uuid4()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(value, encoding="utf-8")
    os.replace(temp, path)
    return value


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _new_pkce() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def _authorization_url(
    *,
    client_id: str,
    redirect_uri: str,
    host_id: str,
    state: str,
    nonce: str,
    challenge: str,
) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "resource": RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "ext_agent_host_id": host_id,
        "agent_name_hint": AGENT_NAME,
    }
    return AUTHORIZATION_ENDPOINT + "?" + urllib.parse.urlencode(params)


def _post_form(url: str, values: Mapping[str, str], *, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(dict(values)).encode("ascii"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "PalWakf-C7R-Phase-A/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        raise C7RPhaseAError(f"OAUTH_HTTP_{exc.code}:{body}") from exc
    except Exception as exc:
        raise C7RPhaseAError(f"OAUTH_NETWORK_FAILURE:{type(exc).__name__}") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise C7RPhaseAError("OAUTH_RESPONSE_INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise C7RPhaseAError("OAUTH_RESPONSE_MUST_BE_OBJECT")
    return payload


def _validate_id_token(id_token: str, *, client_id: str, nonce: str) -> dict[str, Any]:
    try:
        key = PyJWKClient(JWKS_URI).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=client_id,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except Exception as exc:
        raise C7RPhaseAError(f"ID_TOKEN_VALIDATION_FAILED:{type(exc).__name__}") from exc
    if claims.get("nonce") != nonce:
        raise C7RPhaseAError("ID_TOKEN_NONCE_MISMATCH")
    return dict(claims)


def _scope_set(token_payload: Mapping[str, Any]) -> set[str]:
    raw = token_payload.get("scope") or ""
    if isinstance(raw, str):
        return {part for part in raw.split() if part}
    if isinstance(raw, list):
        return {str(part) for part in raw}
    return set()


def _credential_status() -> dict[str, Any]:
    paths = _paths()
    credentials = _protected_read_json(paths["credentials"])
    registration = _read_json(paths["registration"])
    safe: dict[str, Any] = {
        "credential_present": credentials is not None,
        "registration_present": registration is not None,
        "host_id_present": paths["host_id"].is_file(),
        "tokens_exposed": False,
    }
    if registration:
        safe.update(
            {
                "client_id": registration.get("client_id"),
                "subject_sha256": registration.get("subject_sha256"),
                "scopes": registration.get("scopes", []),
                "access_expires_at": registration.get("access_expires_at"),
            }
        )
    return safe


def _runtime_admission(ctx: Any) -> dict[str, Any]:
    marker = _read_json(_paths()["runtime_admission"])
    if not marker:
        raise C7RPhaseAError("C7R_RUNTIME_ADMISSION_MARKER_MISSING")
    source_head = str(marker.get("agentic_source_head") or "").lower()
    source_branch = str(marker.get("agentic_source_branch") or "")
    if source_head != str(ctx.expected_base_sha).lower():
        raise C7RPhaseAError("C7R_RUNTIME_SOURCE_HEAD_MISMATCH")
    if source_branch != str(ctx.task_branch):
        raise C7RPhaseAError("C7R_RUNTIME_SOURCE_BRANCH_MISMATCH")
    if marker.get("capability_id") != "c7r.phase_a":
        raise C7RPhaseAError("C7R_RUNTIME_CAPABILITY_MARKER_INVALID")
    return {
        "agentic_source_head": source_head,
        "agentic_source_branch": source_branch,
        "capability_id": "c7r.phase_a",
        "admitted_at": marker.get("admitted_at"),
    }


def _codex_executable() -> Path:
    candidate = shutil.which("codex")
    if not candidate:
        raise C7RPhaseAError("CODEX_NOT_FOUND")
    return Path(candidate).resolve()


def _codex_preflight() -> dict[str, Any]:
    exe = _codex_executable()
    completed = subprocess.run(
        [str(exe), "--version"],
        capture_output=True,
        text=True,
        shell=False,
        timeout=30,
        check=False,
    )
    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        raise C7RPhaseAError("CODEX_VERSION_READBACK_FAILED")
    if CODEX_VERSION_PIN not in output:
        raise C7RPhaseAError(f"CODEX_VERSION_MISMATCH:{output[:120]}")
    digest = None
    digest_match = None
    if exe.is_file() and exe.suffix.lower() == ".exe":
        digest = hashlib.sha256(exe.read_bytes()).hexdigest()
        digest_match = digest == WINDOWS_X86_64_SHA256
    return {
        "codex_path": str(exe),
        "codex_version": CODEX_VERSION_PIN,
        "version_readback": output[:120],
        "binary_sha256": digest,
        "binary_sha256_matches_pinned_asset": digest_match,
        "normal_openai_api_key_required": False,
        "normal_codex_api_key_required": False,
    }


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _python_executable() -> Path:
    candidate = Path(sys.base_prefix) / ("python.exe" if os.name == "nt" else "bin/python")
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def _oauth_prepare() -> dict[str, Any]:
    paths = _paths()
    paths["root"].mkdir(parents=True, exist_ok=True)
    host_id = _stable_host_id()
    credentials = _protected_read_json(paths["credentials"])
    existing_client = str(credentials.get("client_id")) if credentials else ""
    client_id = existing_client or "dynamic_agent_client"
    verifier, challenge = _new_pkce()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    port = _reserve_loopback_port()
    redirect_uri = f"http://127.0.0.1:{port}/auth/callback"
    pending = {
        "client_id": client_id,
        "dynamic_registration": not bool(existing_client),
        "host_id": host_id,
        "state": state,
        "nonce": nonce,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
        "resource": RESOURCE,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
    }
    _protected_write_json(paths["pending"], pending)
    url = _authorization_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        host_id=host_id,
        state=state,
        nonce=nonce,
        challenge=challenge,
    )
    paths["auth_url"].write_text(url, encoding="utf-8")
    command = [
        str(_python_executable()),
        "-m",
        "palwakf_local_agents.c7r_phase_a_v1",
        "callback",
        "--port",
        str(port),
    ]
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            if os.name == "nt"
            else 0
        ),
    )
    browser_launched = False
    try:
        browser_launched = bool(webbrowser.open(url, new=1, autoraise=True))
    except Exception:
        browser_launched = False
    _safe_write_json(
        paths["status"],
        {
            "state": "OAUTH_PENDING",
            "updated_at": datetime.now(UTC).isoformat(),
            "browser_launch_attempted": True,
            "browser_launch_reported_success": browser_launched,
            "callback_port": port,
            "tokens_exposed": False,
        },
    )
    return {
        "operation": "oauth_prepare",
        "state": "OAUTH_PENDING",
        "browser_launch_attempted": True,
        "browser_launch_reported_success": browser_launched,
        "callback_port": port,
        "authorization_url_local_file": str(paths["auth_url"]),
        "tokens_exposed": False,
        "manual_terminal_required": False,
    }


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    server_version = "PalWakfC7R/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/auth/callback":
            self.send_error(404)
            return
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        try:
            result = _complete_oauth_callback(params)
            message = "PalWakf ChatGPT authorization completed. You may close this window."
            code = 200
        except Exception as exc:
            _safe_write_json(
                _paths()["status"],
                {
                    "state": "OAUTH_FAILED",
                    "error": f"{type(exc).__name__}:{str(exc)[:300]}",
                    "updated_at": datetime.now(UTC).isoformat(),
                    "tokens_exposed": False,
                },
            )
            result = None
            message = "PalWakf authorization failed closed. Return to the application."
            code = 400
        body = (
            "<!doctype html><meta charset='utf-8'><title>PalWakf</title>"
            f"<h1>{message}</h1>"
        ).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self.server.callback_result = result  # type: ignore[attr-defined]


def _single(params: Mapping[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    return values[0] if values else None


def _complete_oauth_callback(params: Mapping[str, list[str]]) -> dict[str, Any]:
    paths = _paths()
    pending = _protected_read_json(paths["pending"])
    if not pending:
        raise C7RPhaseAError("OAUTH_PENDING_STATE_MISSING")
    if _single(params, "state") != pending.get("state"):
        raise C7RPhaseAError("OAUTH_STATE_MISMATCH")
    error = _single(params, "error")
    if error:
        raise C7RPhaseAError(f"OAUTH_CALLBACK_ERROR:{error}")
    code = _single(params, "code")
    if not code:
        raise C7RPhaseAError("OAUTH_CODE_MISSING")

    callback_client_id = _single(params, "client_id")
    dynamic = bool(pending.get("dynamic_registration"))
    if dynamic:
        if not callback_client_id or callback_client_id == "dynamic_agent_client":
            raise C7RPhaseAError("ISSUED_CLIENT_ID_MISSING")
        exchange_client_id = callback_client_id
    else:
        expected_client = str(pending.get("client_id") or "")
        if callback_client_id and callback_client_id != expected_client:
            raise C7RPhaseAError("ISSUED_CLIENT_ID_CHANGED")
        exchange_client_id = expected_client

    token = _post_form(
        TOKEN_ENDPOINT,
        {
            "grant_type": "authorization_code",
            "client_id": exchange_client_id,
            "code": code,
            "code_verifier": str(pending["code_verifier"]),
            "redirect_uri": str(pending["redirect_uri"]),
            "resource": RESOURCE,
        },
    )
    for required in ("access_token", "refresh_token", "id_token", "expires_in"):
        if not token.get(required):
            raise C7RPhaseAError(f"TOKEN_FIELD_MISSING:{required}")
    scopes = _scope_set(token)
    if "chatgpt.tokens.use.direct" not in scopes:
        raise C7RPhaseAError("CHATGPT_PLAN_SCOPE_NOT_GRANTED")
    claims = _validate_id_token(
        str(token["id_token"]),
        client_id=exchange_client_id,
        nonce=str(pending["nonce"]),
    )
    expires_at = datetime.now(UTC) + timedelta(seconds=int(token["expires_in"]))
    credentials = {
        "client_id": exchange_client_id,
        "host_id": str(pending["host_id"]),
        "access_token": str(token["access_token"]),
        "refresh_token": str(token["refresh_token"]),
        "id_token": str(token["id_token"]),
        "scope": sorted(scopes),
        "access_expires_at": expires_at.isoformat(),
        "earliest_refresh_at": token.get("earliest_refresh_at"),
        "subject": str(claims["sub"]),
    }
    _protected_write_json(paths["credentials"], credentials)
    subject_hash = hashlib.sha256(str(claims["sub"]).encode("utf-8")).hexdigest()
    registration = {
        "schema": "palwakf.c7r.registration.v1",
        "client_id": exchange_client_id,
        "host_id": str(pending["host_id"]),
        "subject_sha256": subject_hash,
        "scopes": sorted(scopes),
        "access_expires_at": expires_at.isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "tokens_exposed": False,
    }
    _safe_write_json(paths["registration"], registration)
    _safe_write_json(
        paths["status"],
        {
            "state": "OAUTH_AUTHENTICATED",
            "updated_at": datetime.now(UTC).isoformat(),
            "client_id": exchange_client_id,
            "subject_sha256": subject_hash,
            "scopes": sorted(scopes),
            "access_expires_at": expires_at.isoformat(),
            "tokens_exposed": False,
        },
    )
    try:
        paths["pending"].unlink(missing_ok=True)
        paths["auth_url"].unlink(missing_ok=True)
    except OSError:
        pass
    return registration


def _run_callback_server(port: int) -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.timeout = 600
    server.handle_request()


@contextmanager
def _exclusive_refresh_lock(timeout_seconds: float = 10.0) -> Iterator[None]:
    path = _paths()["refresh_lock"]
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise C7RPhaseAError("REFRESH_LOCK_TIMEOUT")
            time.sleep(0.1)
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    finally:
        os.close(fd)
        try:
            path.unlink()
        except OSError:
            pass


def _credentials_with_refresh() -> dict[str, Any]:
    paths = _paths()
    credentials = _protected_read_json(paths["credentials"])
    if not credentials:
        raise C7RPhaseAError("CHATGPT_CREDENTIALS_MISSING")
    try:
        expires = datetime.fromisoformat(
            str(credentials["access_expires_at"]).replace("Z", "+00:00")
        )
    except Exception as exc:
        raise C7RPhaseAError("ACCESS_EXPIRY_INVALID") from exc
    if expires > datetime.now(UTC) + timedelta(minutes=2):
        return credentials
    with _exclusive_refresh_lock():
        credentials = _protected_read_json(paths["credentials"])
        if not credentials:
            raise C7RPhaseAError("CHATGPT_CREDENTIALS_MISSING")
        expires = datetime.fromisoformat(
            str(credentials["access_expires_at"]).replace("Z", "+00:00")
        )
        if expires > datetime.now(UTC) + timedelta(minutes=2):
            return credentials
        refreshed = _post_form(
            TOKEN_ENDPOINT,
            {
                "grant_type": "refresh_token",
                "client_id": str(credentials["client_id"]),
                "refresh_token": str(credentials["refresh_token"]),
                "resource": RESOURCE,
            },
        )
        if not refreshed.get("access_token") or not refreshed.get("refresh_token"):
            raise C7RPhaseAError("REFRESH_TOKEN_RESPONSE_INCOMPLETE")
        scopes = _scope_set(refreshed) or set(credentials.get("scope") or [])
        if "chatgpt.tokens.use.direct" not in scopes:
            raise C7RPhaseAError("CHATGPT_PLAN_SCOPE_LOST")
        expires_at = datetime.now(UTC) + timedelta(
            seconds=int(refreshed.get("expires_in") or 3600)
        )
        credentials.update(
            {
                "access_token": str(refreshed["access_token"]),
                "refresh_token": str(refreshed["refresh_token"]),
                "id_token": str(refreshed.get("id_token") or credentials.get("id_token") or ""),
                "scope": sorted(scopes),
                "access_expires_at": expires_at.isoformat(),
                "earliest_refresh_at": refreshed.get("earliest_refresh_at"),
            }
        )
        _protected_write_json(paths["credentials"], credentials)
        registration = _read_json(paths["registration"]) or {}
        registration["scopes"] = sorted(scopes)
        registration["access_expires_at"] = expires_at.isoformat()
        registration["updated_at"] = datetime.now(UTC).isoformat()
        registration["tokens_exposed"] = False
        _safe_write_json(paths["registration"], registration)
        return credentials


def _model_for_account(access_token: str, requested: str | None) -> str:
    request = urllib.request.Request(
        RESOURCE + "/models",
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": "PalWakf-C7R-Phase-A/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise C7RPhaseAError(f"MODEL_LIST_HTTP_{exc.code}") from exc
    except Exception as exc:
        raise C7RPhaseAError(f"MODEL_LIST_FAILED:{type(exc).__name__}") from exc
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise C7RPhaseAError("MODEL_LIST_INVALID")
    visible = [
        item for item in models
        if isinstance(item, dict)
        and item.get("visibility") == "list"
        and isinstance(item.get("slug"), str)
    ]
    slugs = [str(item["slug"]) for item in visible]
    if requested:
        if requested not in slugs:
            raise C7RPhaseAError("REQUESTED_MODEL_NOT_IN_ACCOUNT_CATALOG")
        return requested
    if not slugs:
        raise C7RPhaseAError("NO_VISIBLE_CHATGPT_PLAN_MODEL")
    return slugs[0]


def _app_server_command(codex: Path) -> list[str]:
    return [
        str(codex),
        "app-server",
        "--listen",
        "stdio://",
        "-c",
        'model_provider="openai_chatgpt_plan"',
        "-c",
        'model_providers.openai_chatgpt_plan.name="ChatGPT plan"',
        "-c",
        'model_providers.openai_chatgpt_plan.base_url="https://api.openai.com/v1"',
        "-c",
        'model_providers.openai_chatgpt_plan.env_key="ACCESS_TOKEN"',
        "-c",
        'model_providers.openai_chatgpt_plan.wire_api="responses"',
        "-c",
        "model_providers.openai_chatgpt_plan.requires_openai_auth=false",
        "-c",
        "model_providers.openai_chatgpt_plan.supports_websockets=false",
    ]


class _JsonLineClient:
    def __init__(self, process: subprocess.Popen[str]) -> None:
        self.process = process
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.malformed = False
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                self.malformed = True
                continue
            if isinstance(value, dict):
                self.messages.put(value)
            else:
                self.malformed = True

    def send(self, payload: Mapping[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(dict(payload), separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def wait(self, predicate: Any, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise C7RPhaseAError("APP_SERVER_EVENT_TIMEOUT")
            try:
                item = self.messages.get(timeout=min(remaining, 1.0))
            except queue.Empty:
                if self.process.poll() is not None:
                    raise C7RPhaseAError("APP_SERVER_EXITED_EARLY")
                continue
            if predicate(item):
                return item


def _synthetic_inference(repo_root: str, requested_model: str | None) -> dict[str, Any]:
    preflight = _codex_preflight()
    credentials = _credentials_with_refresh()
    access_token = str(credentials["access_token"])
    model = _model_for_account(access_token, requested_model)
    codex = Path(str(preflight["codex_path"]))
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env.pop("CODEX_API_KEY", None)
    env["ACCESS_TOKEN"] = access_token
    process = subprocess.Popen(
        _app_server_command(codex),
        cwd=repo_root,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        shell=False,
    )
    client = _JsonLineClient(process)
    output_parts: list[str] = []
    try:
        client.send(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "PalWakf",
                        "title": "PalWakf",
                        "version": "1.0.0",
                    }
                },
            }
        )
        initialized = client.wait(lambda item: item.get("id") == 1, 30)
        if initialized.get("error"):
            raise C7RPhaseAError("APP_SERVER_INITIALIZE_FAILED")
        client.send({"method": "initialized", "params": {}})
        client.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": model,
                    "modelProvider": "openai_chatgpt_plan",
                    "cwd": repo_root,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "ephemeral": True,
                },
            }
        )
        thread_started = client.wait(lambda item: item.get("id") == 2, 60)
        if thread_started.get("error"):
            raise C7RPhaseAError("APP_SERVER_THREAD_START_FAILED")
        result = thread_started.get("result")
        thread = result.get("thread") if isinstance(result, dict) else None
        thread_id = thread.get("id") if isinstance(thread, dict) else None
        if not isinstance(thread_id, str) or not thread_id:
            raise C7RPhaseAError("APP_SERVER_THREAD_ID_MISSING")
        client.send(
            {
                "id": 3,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": SYNTHETIC_PROMPT}],
                },
            }
        )
        start_response = client.wait(lambda item: item.get("id") == 3, 60)
        if start_response.get("error"):
            raise C7RPhaseAError("APP_SERVER_TURN_START_FAILED")

        deadline = time.monotonic() + 180
        completed: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            item = client.wait(lambda _: True, max(1.0, deadline - time.monotonic()))
            if item.get("method") == "item/agentMessage/delta":
                params = item.get("params")
                if isinstance(params, dict) and isinstance(params.get("delta"), str):
                    output_parts.append(str(params["delta"]))
            if item.get("method") == "turn/completed":
                completed = item
                break
        if completed is None:
            raise C7RPhaseAError("TURN_COMPLETED_NOT_OBSERVED")
        params = completed.get("params")
        turn = params.get("turn") if isinstance(params, dict) else None
        status = turn.get("status") if isinstance(turn, dict) else None
        if status != "completed":
            detail = json.dumps(completed, ensure_ascii=False)
            if (
                "subscription_sharing_usage_limit_exceeded" in detail
                or "subscription_sharing_usage_unavailable" in detail
            ):
                raise C7RPhaseAError("QUOTA_HOLD")
            raise C7RPhaseAError(f"TURN_NOT_COMPLETED:{status}")
        text = "".join(output_parts).strip()
        if SYNTHETIC_EXPECTED not in text:
            raise C7RPhaseAError("SYNTHETIC_RESPONSE_MISMATCH")
        return {
            "operation": "inference",
            "state": "COMPLETED",
            "provider": "openai_chatgpt_plan",
            "wire_api": "responses",
            "store": False,
            "stream": True,
            "websockets": False,
            "model": model,
            "thread_id_sha256": hashlib.sha256(thread_id.encode("utf-8")).hexdigest(),
            "synthetic_response": SYNTHETIC_EXPECTED,
            "normal_openai_api_key_used": False,
            "normal_codex_api_key_used": False,
            "tokens_exposed": False,
        }
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def _with_evidence_summary(result: Mapping[str, Any]) -> Mapping[str, Any]:
    value = dict(result)
    operation = str(value.get("operation") or "unknown")
    safe: dict[str, Any] = {"operation": operation, "tokens_exposed": False}
    if operation == "preflight":
        runtime = value.get("runtime")
        codex = value.get("codex")
        oauth = value.get("oauth")
        if isinstance(runtime, Mapping):
            safe.update(
                {
                    "agentic_source_head": runtime.get("agentic_source_head"),
                    "agentic_source_branch": runtime.get("agentic_source_branch"),
                    "runtime_capability": runtime.get("capability_id"),
                }
            )
        if isinstance(codex, Mapping):
            safe.update(
                {
                    "codex_version": codex.get("codex_version"),
                    "binary_sha256_matches_pinned_asset": codex.get(
                        "binary_sha256_matches_pinned_asset"
                    ),
                    "normal_openai_api_key_required": False,
                    "normal_codex_api_key_required": False,
                }
            )
        if isinstance(oauth, Mapping):
            safe.update(
                {
                    "credential_present": oauth.get("credential_present"),
                    "registration_present": oauth.get("registration_present"),
                }
            )
    elif operation == "oauth_prepare":
        safe.update(
            {
                "state": value.get("state"),
                "browser_launch_attempted": value.get("browser_launch_attempted"),
                "browser_launch_reported_success": value.get(
                    "browser_launch_reported_success"
                ),
                "manual_terminal_required": False,
            }
        )
    elif operation == "oauth_status":
        status = value.get("status")
        credentials = value.get("credentials")
        if isinstance(status, Mapping):
            safe["state"] = status.get("state")
        if isinstance(credentials, Mapping):
            safe.update(
                {
                    "credential_present": credentials.get("credential_present"),
                    "registration_present": credentials.get("registration_present"),
                    "scopes": credentials.get("scopes", []),
                    "access_expires_at": credentials.get("access_expires_at"),
                }
            )
    elif operation == "inference":
        safe.update(
            {
                "state": value.get("state"),
                "provider": value.get("provider"),
                "wire_api": value.get("wire_api"),
                "store": value.get("store"),
                "stream": value.get("stream"),
                "websockets": value.get("websockets"),
                "model": value.get("model"),
                "synthetic_response": value.get("synthetic_response"),
                "normal_openai_api_key_used": False,
                "normal_codex_api_key_used": False,
            }
        )
    value["_evidence_summary"] = json.dumps(
        safe,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return value


def c7r_phase_a(ctx: Any, args: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = str(args.get("operation") or "")
    allowed = {"preflight", "oauth_prepare", "oauth_status", "inference"}
    if operation not in allowed:
        raise C7RPhaseAError("C7R_OPERATION_NOT_ADMITTED")
    root = _state_root().resolve()
    scopes = {Path(item).resolve() for item in ctx.scope_paths}
    if root not in scopes:
        raise C7RPhaseAError("C7R_STATE_ROOT_NOT_IN_TASK_SCOPE")
    runtime = _runtime_admission(ctx)

    if operation == "preflight":
        return _with_evidence_summary(
            {
                "operation": "preflight",
                "state_root": str(root),
                "runtime": runtime,
                "codex": _codex_preflight(),
                "oauth": _credential_status(),
                "tokens_exposed": False,
                "manual_terminal_required": False,
            }
        )
    if operation == "oauth_prepare":
        return _with_evidence_summary(_oauth_prepare())
    if operation == "oauth_status":
        status = _read_json(_paths()["status"]) or {"state": "NOT_STARTED"}
        return _with_evidence_summary(
            {
                "operation": "oauth_status",
                "status": status,
                "credentials": _credential_status(),
                "tokens_exposed": False,
            }
        )
    if operation == "inference":
        requested_model = args.get("model")
        if requested_model is not None and not isinstance(requested_model, str):
            raise C7RPhaseAError("MODEL_MUST_BE_STRING")
        return _with_evidence_summary(_synthetic_inference(str(root), requested_model))
    raise AssertionError(operation)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("callback",))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if args.command == "callback":
        _run_callback_server(args.port)


if __name__ == "__main__":
    main()
