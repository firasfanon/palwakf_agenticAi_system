from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from palwakf_local_agents.github_issue_transport_v1 import (
    TERMINAL_STATES,
    TransportError,
)
from palwakf_local_agents.windows_protected_secret_v1 import (
    ProtectedSecretError,
    read_windows_protected_text,
)


class DriveRemoteIntentError(TransportError):
    pass


class DriveClientInboxV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: str = Field(pattern=r"^[a-z][a-z0-9_.:-]{1,63}$")
    inbox_path: str = Field(min_length=1, max_length=500)


class RcloneDriveRemoteIntentSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rclone_executable: str
    rclone_config_path: str | None = None
    rclone_config_protected_path: str | None = None
    remote_name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")
    client_inboxes: tuple[DriveClientInboxV1, ...] = Field(min_length=1, max_length=16)
    results_path: str
    archive_path: str
    state_dir: str
    authority_python: str
    authority_cli_path: str
    authority_src_path: str
    authority_key_path: str
    authority_key_id: str
    authority_key_machine_scope: bool = False
    max_intent_bytes: int = Field(default=262144, ge=1024, le=1048576)
    command_timeout_seconds: int = Field(default=60, ge=5, le=300)

    @model_validator(mode="after")
    def validate_config_source(self) -> "RcloneDriveRemoteIntentSettingsV1":
        configured = [
            bool(self.rclone_config_path),
            bool(self.rclone_config_protected_path),
        ]
        if sum(configured) != 1:
            raise ValueError("EXACTLY_ONE_RCLONE_CONFIG_SOURCE_REQUIRED")
        return self

    @field_validator("results_path", "archive_path")
    @classmethod
    def validate_remote_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/").strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("DRIVE_REMOTE_PATH_INVALID")
        return normalized

    @field_validator("client_inboxes")
    @classmethod
    def validate_clients(
        cls,
        value: tuple[DriveClientInboxV1, ...],
    ) -> tuple[DriveClientInboxV1, ...]:
        ids = [item.client_id for item in value]
        paths = [item.inbox_path.casefold() for item in value]
        if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
            raise ValueError("DRIVE_CLIENT_INBOXES_MUST_BE_UNIQUE")
        return value


Runner = Callable[[list[str], int], subprocess.CompletedProcess[bytes]]


def _subprocess_runner(
    argv: list[str],
    timeout: int,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        shell=False,
        capture_output=True,
        text=False,
        timeout=timeout,
        check=False,
    )


class RcloneWorkspaceDriveRemoteIntentTransportV1:
    transport_id = "workspace-drive-remote-intent-v1"

    def __init__(
        self,
        settings: RcloneDriveRemoteIntentSettingsV1,
        *,
        runner: Runner | None = None,
    ) -> None:
        self.settings = settings
        self._runner = runner or _subprocess_runner
        self._state_dir = Path(settings.state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._processed_path = self._state_dir / "drive-intent-processed.json"
        self._processed = self._load_processed()

    def _load_processed(self) -> set[str]:
        if not self._processed_path.is_file():
            return set()
        try:
            raw = json.loads(self._processed_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DriveRemoteIntentError("DRIVE_PROCESSED_LEDGER_INVALID") from exc
        if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
            raise DriveRemoteIntentError("DRIVE_PROCESSED_LEDGER_INVALID")
        return set(raw)

    def _save_processed(self) -> None:
        temp = self._processed_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(sorted(self._processed), ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temp, self._processed_path)

    def _remote(self, path: str) -> str:
        normalized = path.replace("\\", "/").strip("/")
        if not normalized or ".." in normalized.split("/"):
            raise DriveRemoteIntentError("DRIVE_REMOTE_PATH_INVALID")
        return f"{self.settings.remote_name}:{normalized}"

    def _run_rclone(self, args: list[str]) -> subprocess.CompletedProcess[bytes]:
        allowed = {"lsjson", "cat", "copyto", "moveto"}
        if not args or args[0] not in allowed:
            raise DriveRemoteIntentError("RCLONE_VERB_NOT_ALLOWED")

        def invoke(config_path: str) -> subprocess.CompletedProcess[bytes]:
            argv = [
                self.settings.rclone_executable,
                "--config",
                config_path,
                *args,
            ]
            try:
                return self._runner(argv, self.settings.command_timeout_seconds)
            except (OSError, subprocess.SubprocessError) as exc:
                raise DriveRemoteIntentError(
                    f"RCLONE_EXECUTION_FAILED:{type(exc).__name__}"
                ) from exc

        if self.settings.rclone_config_path:
            result = invoke(self.settings.rclone_config_path)
        else:
            try:
                config_text = read_windows_protected_text(
                    str(self.settings.rclone_config_protected_path)
                )
            except ProtectedSecretError as exc:
                raise DriveRemoteIntentError("RCLONE_PROTECTED_CONFIG_UNAVAILABLE") from exc
            with tempfile.TemporaryDirectory(
                prefix="palwakf-rclone-config-",
                dir=self._state_dir,
            ) as temp_dir:
                config_file = Path(temp_dir) / "rclone.conf"
                config_file.write_text(config_text, encoding="utf-8")
                result = invoke(str(config_file))
        if result.returncode != 0:
            raise DriveRemoteIntentError(f"RCLONE_{args[0].upper()}_FAILED")
        return result

    @staticmethod
    def _safe_item_name(value: Any) -> str:
        name = str(value or "")
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise DriveRemoteIntentError("DRIVE_ITEM_NAME_INVALID")
        return name

    def _list_items(self, inbox: DriveClientInboxV1) -> list[dict[str, Any]]:
        result = self._run_rclone(
            [
                "lsjson",
                self._remote(inbox.inbox_path),
                "--files-only",
                "--metadata",
                "--max-depth",
                "1",
            ]
        )
        try:
            payload = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DriveRemoteIntentError("RCLONE_LSJSON_INVALID") from exc
        if not isinstance(payload, list):
            raise DriveRemoteIntentError("RCLONE_LSJSON_INVALID")
        items = [item for item in payload if isinstance(item, dict)]
        return sorted(items, key=lambda item: str(item.get("Path") or item.get("Name") or ""))

    def _item_key(
        self,
        inbox: DriveClientInboxV1,
        item: Mapping[str, Any],
    ) -> str:
        remote_id = item.get("ID") or item.get("Id")
        name = self._safe_item_name(item.get("Path") or item.get("Name"))
        stable = str(remote_id or f"{inbox.client_id}:{name}")
        return hashlib.sha256(stable.encode("utf-8")).hexdigest()

    def _copy_intent_to_local(
        self,
        inbox: DriveClientInboxV1,
        item: Mapping[str, Any],
        target: Path,
    ) -> str:
        del target
        name = self._safe_item_name(item.get("Path") or item.get("Name"))
        source = self._remote(f"{inbox.inbox_path.rstrip('/')}/{name}")
        result = self._run_rclone(
            [
                "cat",
                source,
                "--count",
                str(self.settings.max_intent_bytes + 1),
            ]
        )
        data = result.stdout
        if len(data) > self.settings.max_intent_bytes:
            raise DriveRemoteIntentError("REMOTE_INTENT_TOO_LARGE")
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DriveRemoteIntentError("REMOTE_INTENT_NOT_UTF8") from exc
    @staticmethod
    def _parse_remote_intent(text: str, expected_client_id: str) -> dict[str, Any]:
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DriveRemoteIntentError("REMOTE_INTENT_JSON_INVALID") from exc
        if not isinstance(raw, dict):
            raise DriveRemoteIntentError("REMOTE_INTENT_MUST_BE_OBJECT")
        client_id = raw.get("client_id")
        if client_id is not None and client_id != expected_client_id:
            raise DriveRemoteIntentError("REMOTE_INTENT_CLIENT_ID_MISMATCH")
        raw["client_id"] = expected_client_id
        if raw.get("schema_id") not in {None, "palwakf.remote_intent.v1"}:
            raise DriveRemoteIntentError("REMOTE_INTENT_SCHEMA_INVALID")
        raw["schema_id"] = "palwakf.remote_intent.v1"
        if not isinstance(raw.get("payload"), dict):
            raise DriveRemoteIntentError("REMOTE_INTENT_PAYLOAD_REQUIRED")
        return raw

    def _authorize(
        self,
        remote_intent: Mapping[str, Any],
        input_path: Path,
        output_path: Path,
    ) -> Mapping[str, Any]:
        input_path.write_text(
            json.dumps(dict(remote_intent), ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = self.settings.authority_src_path
        argv = [
            self.settings.authority_python,
            self.settings.authority_cli_path,
            "--key-path",
            self.settings.authority_key_path,
            "--key-id",
            self.settings.authority_key_id,
        ]
        if self.settings.authority_key_machine_scope:
            argv.append("--machine-scope-key")
        argv.extend(
            [
                "authorize-intent",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ]
        )
        try:
            completed = subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=False,
                timeout=self.settings.command_timeout_seconds,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DriveRemoteIntentError(
                f"WORKSPACE_AUTHORITY_EXECUTION_FAILED:{type(exc).__name__}"
            ) from exc
        if completed.returncode != 0:
            raise DriveRemoteIntentError("WORKSPACE_AUTHORITY_REJECTED")
        try:
            signed = json.loads(output_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DriveRemoteIntentError("SIGNED_ENVELOPE_INVALID") from exc
        if not isinstance(signed, dict):
            raise DriveRemoteIntentError("SIGNED_ENVELOPE_INVALID")
        return signed

    def health(self) -> Mapping[str, Any]:
        for inbox in self.settings.client_inboxes:
            self._run_rclone(
                [
                    "lsjson",
                    self._remote(inbox.inbox_path),
                    "--files-only",
                    "--max-depth",
                    "1",
                ]
            )
        return {"transport_id": self.transport_id, "status": "HEALTHY"}

    def claim_task(self, *, executor_id: str) -> Mapping[str, Any] | None:
        for inbox in self.settings.client_inboxes:
            for item in self._list_items(inbox):
                item_key = self._item_key(inbox, item)
                if item_key in self._processed:
                    continue
                name = self._safe_item_name(item.get("Path") or item.get("Name"))
                with tempfile.TemporaryDirectory(
                    prefix="palwakf-drive-intent-",
                    dir=self._state_dir,
                ) as temp_dir:
                    temp_root = Path(temp_dir)
                    local_intent = temp_root / "remote-intent.json"
                    signed_output = temp_root / "signed-envelope.json"
                    text = self._copy_intent_to_local(inbox, item, local_intent)
                    remote_intent = self._parse_remote_intent(text, inbox.client_id)
                    signed = self._authorize(
                        remote_intent,
                        temp_root / "authority-input.json",
                        signed_output,
                    )
                if str(signed.get("executor_id") or "") != executor_id:
                    raise DriveRemoteIntentError("SIGNED_EXECUTOR_ID_MISMATCH")
                return {
                    "item_key": item_key,
                    "client_id": inbox.client_id,
                    "inbox_path": inbox.inbox_path,
                    "name": name,
                    "envelope": signed,
                }
        return None

    def read_envelope(self, claimed: Mapping[str, Any]) -> Mapping[str, Any]:
        envelope = claimed.get("envelope")
        if not isinstance(envelope, dict):
            raise DriveRemoteIntentError("CLAIMED_ENVELOPE_MISSING")
        return envelope

    def publish_progress(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        del claimed, payload

    def publish_heartbeat(self, payload: Mapping[str, Any]) -> None:
        del payload

    def _upload_json(
        self,
        remote_path: str,
        file_name: str,
        payload: Mapping[str, Any],
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="palwakf-drive-result-",
            dir=self._state_dir,
        ) as temp_dir:
            local = Path(temp_dir) / "result.json"
            local.write_text(
                json.dumps(dict(payload), ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            self._run_rclone(
                [
                    "copyto",
                    str(local),
                    self._remote(f"{remote_path.rstrip('/')}/{file_name}"),
                ]
            )

    def publish_result(
        self,
        claimed: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        task_id = str(payload.get("task_id") or claimed.get("item_key") or "result")
        safe_name = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:24]
        self._upload_json(
            self.settings.results_path,
            f"{safe_name}.result.json",
            payload,
        )

    def ack_task(self, claimed: Mapping[str, Any], *, status: str) -> None:
        if status not in TERMINAL_STATES:
            return
        inbox = str(claimed.get("inbox_path") or "")
        name = self._safe_item_name(claimed.get("name"))
        client_id = str(claimed.get("client_id") or "")
        item_key = str(claimed.get("item_key") or "")
        if not inbox or not client_id or not item_key:
            raise DriveRemoteIntentError("DRIVE_CLAIM_METADATA_MISSING")
        source = self._remote(f"{inbox.rstrip('/')}/{name}")
        destination = self._remote(
            f"{self.settings.archive_path.rstrip('/')}/{client_id}/{item_key}-{name}"
        )
        self._run_rclone(["moveto", source, destination])
        self._processed.add(item_key)
        self._save_processed()

    def release_or_fail(
        self,
        claimed: Mapping[str, Any],
        *,
        reason: str,
    ) -> None:
        item_key = str(claimed.get("item_key") or "unknown")
        self._upload_json(
            self.settings.results_path,
            f"{item_key[:24]}.failure.json",
            {
                "status": "BLOCKED",
                "reason": str(reason)[:300],
                "transport_id": self.transport_id,
            },
        )
