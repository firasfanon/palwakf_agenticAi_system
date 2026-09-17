from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import yaml

from .contracts import ProviderId, RunRequest
from .qa_security_review import run_independent_review
from .test_execution import run_controlled_tests


class ModelProvider(ABC):
    provider_id: str

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...

    @abstractmethod
    def generate(self, model: str, prompt: str, *, json_mode: bool = False, timeout: int = 60) -> dict[str, Any]: ...


class OllamaProvider(ModelProvider):
    provider_id = "ollama"

    def __init__(self, endpoint: str | None = None):
        self.endpoint = (endpoint or os.getenv("PALWAKF_OLLAMA_ENDPOINT") or "http://127.0.0.1:11434").rstrip("/")

    def _request(self, path: str, payload: dict[str, Any] | None = None, timeout: int = 10) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.endpoint + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def list_models(self) -> list[str]:
        return [m["name"] for m in self._request("/api/tags").get("models", []) if m.get("name")]

    def health(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            models = self.list_models()
            return {
                "provider_id": self.provider_id,
                "healthy": True,
                "models": models,
                "capabilities": ["generate", "structured_output", "health", "list_models"],
                "latency_ms": round((time.perf_counter()-started)*1000, 2),
                "locality": "LOCAL_ENDPOINT",
                "privacy": "LOCAL_BY_ENDPOINT_POLICY",
            }
        except Exception as error:
            return {
                "provider_id": self.provider_id,
                "healthy": False,
                "models": [],
                "error": f"{type(error).__name__}: {error}",
                "latency_ms": round((time.perf_counter()-started)*1000, 2),
            }

    def generate(self, model: str, prompt: str, *, json_mode: bool = False, timeout: int = 60) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if json_mode:
            payload["format"] = "json"
        started = time.perf_counter()
        result = self._request("/api/generate", payload, timeout)
        return {
            "model": result.get("model", model),
            "response": result.get("response", ""),
            "latency_ms": round((time.perf_counter()-started)*1000, 2),
        }


class ExecutionProvider(ABC):
    provider_id: ProviderId

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def execute_read_only(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]: ...

    def execute_independent_review(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        raise RuntimeError("INDEPENDENT_REVIEW_NOT_SUPPORTED_BY_PROVIDER")

    def execute_controlled_tests(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        raise RuntimeError("CONTROLLED_TEST_EXECUTION_NOT_SUPPORTED_BY_PROVIDER")

    def execute_bounded_write(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        raise RuntimeError("BOUNDED_WRITE_NOT_SUPPORTED_BY_PROVIDER")


def _authorized_files(project_root: Path, request: RunRequest) -> tuple[list[tuple[Path, str, int]], int]:
    budget = request.environment.resource_budget
    policy = request.environment.filesystem_policy
    patterns = policy.allowed_patterns
    project_root = project_root.resolve()
    roots = [Path(root).resolve() for root in policy.allowed_roots]
    if not roots:
        raise RuntimeError("FILESYSTEM_ROOT_REQUIRED")

    files: list[tuple[Path, str, int]] = []
    bytes_seen = 0
    for path in project_root.rglob("*"):
        if len(files) >= budget.max_files:
            break
        if (
            ".git" in path.parts
            or ".palwakf_apply_backup" in path.parts
            or path.is_symlink()
            or not path.is_file()
        ):
            continue

        resolved = path.resolve()
        try:
            resolved.relative_to(project_root)
        except ValueError:
            continue

        within_authorized_root = False
        for root in roots:
            try:
                resolved.relative_to(root)
                within_authorized_root = True
                break
            except ValueError:
                continue
        if not within_authorized_root:
            continue

        relative = resolved.relative_to(project_root).as_posix()
        if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
            continue
        size = resolved.stat().st_size
        if bytes_seen + size > budget.max_bytes:
            break
        bytes_seen += size
        files.append((resolved, relative, size))
    return files, bytes_seen


def _bounded_mutation_target(project_root: Path, request: RunRequest, raw_path: str) -> tuple[Path, str]:
    project_root = project_root.resolve()
    normalized = raw_path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = pure.parts
    if (
        not parts
        or pure.is_absolute()
        or normalized.startswith("/")
        or (len(normalized) >= 2 and normalized[1] == ":")
        or any(part in {"", ".", "..", ".git"} for part in parts)
    ):
        raise RuntimeError("BOUNDED_WRITE_PATH_INVALID")

    cursor = project_root
    for part in parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise RuntimeError("BOUNDED_WRITE_SYMLINK_PATH_DENIED")
    target = project_root.joinpath(*parts)
    if target.is_symlink():
        raise RuntimeError("BOUNDED_WRITE_SYMLINK_TARGET_DENIED")
    if not target.parent.is_dir():
        raise RuntimeError("BOUNDED_WRITE_PARENT_MUST_EXIST")

    parent = target.parent.resolve()
    try:
        parent.relative_to(project_root)
    except ValueError as error:
        raise RuntimeError("BOUNDED_WRITE_PATH_ESCAPE") from error

    roots = [Path(value).resolve() for value in request.environment.filesystem_policy.allowed_roots]
    within_root = False
    for allowed_root in roots:
        try:
            target_parent = parent.relative_to(allowed_root)
            del target_parent
            within_root = True
            break
        except ValueError:
            continue
    if not within_root:
        raise RuntimeError("BOUNDED_WRITE_ROOT_DENIED")

    relative = PurePosixPath(*parts).as_posix()
    patterns = request.environment.filesystem_policy.allowed_patterns
    if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
        raise RuntimeError("BOUNDED_WRITE_SCOPE_DENIED")
    return target, relative


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class NativeProvider(ExecutionProvider):
    provider_id = ProviderId.NATIVE

    def health(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id.value,
            "discovered": True,
            "healthy": True,
            "modes": ["READ_ONLY_DIAGNOSTIC", "BOUNDED_WRITE"],
            "filesystem_policy": "READ_ONLY_DEFAULT_BOUNDED_WRITE_BY_EXTERNAL_ADMISSION",
            "network_policy": "DENY_BY_DEFAULT",
            "cancel_supported": True,
            "timeout_supported": True,
            "operational_write_admission": "EXTERNAL_ADMISSION_REFERENCE_REQUIRED",
        }

    def execute_read_only(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        files, bytes_seen = _authorized_files(project_root, request)
        manifest = [{"path": relative, "size": size} for _, relative, size in files]
        return {
            "provider_id": self.provider_id.value,
            "successful": True,
            "action_type": "READ_ONLY_REPOSITORY_MANIFEST",
            "files": len(manifest),
            "bytes": bytes_seen,
            "observations": [{"manifest_sample": manifest[:50], "objective": request.objective}],
            "errors": [],
            "changed_files": [],
            "process_success": True,
            "policy_success": True,
            "tool_execution_success": True,
            "objective_success": True,
            "postcondition_success": True,
            "tool_call_observed": bool(request.tools),
            "evidence": [],
        }


    def execute_independent_review(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        return run_independent_review(project_root=project_root, request=request)

    def execute_controlled_tests(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        return run_controlled_tests(project_root=project_root, request=request)

    def execute_bounded_write(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        project_root = project_root.resolve()
        if Path(request.environment.worktree).resolve() != project_root:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_WORKTREE_MISMATCH")
        if request.agent_id != "coding_builder_agentic_v1" or request.role_id != "coding_builder":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_CODING_BUILDER_ONLY")
        if request.task_class != "BOUNDED_SOURCE_MUTATION":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_TASK_CLASS_REQUIRED")
        if request.authorization.agent_admission_reference != "PREL5-024":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_ADMISSION_REFERENCE_REQUIRED")
        if request.tools != ["bounded_file_write"] or request.environment.tool_policy != ["bounded_file_write"]:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_TOOL_POLICY_INVALID")
        auth_roots = sorted(str(Path(value).resolve()) for value in request.authorization.allowed_filesystem_roots)
        env_roots = sorted(str(Path(value).resolve()) for value in request.environment.filesystem_policy.allowed_roots)
        if not auth_roots or auth_roots != env_roots:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_ROOT_AUTHORITY_MISMATCH")
        if request.authorization.allowed_path_patterns != request.environment.filesystem_policy.allowed_patterns:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_PATTERN_AUTHORITY_MISMATCH")
        if request.provider_mode != "BOUNDED_WRITE":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_MODE_REQUIRED")
        if request.environment.filesystem_policy.mode != "BOUNDED_WRITE":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_FILESYSTEM_MODE_REQUIRED")
        if request.authorization.read_only:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_AUTHORITY_REQUIRED")
        if request.environment.network_policy.read or request.environment.network_policy.write:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_NETWORK_DENIED")
        if request.environment.db_authority != "NONE":
            raise RuntimeError("NATIVE_BOUNDED_WRITE_DATABASE_DENIED")
        if not request.file_mutations:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_MUTATION_REQUIRED")

        budget = request.environment.resource_budget
        if len(request.file_mutations) > budget.max_files:
            raise RuntimeError("NATIVE_BOUNDED_WRITE_FILE_BUDGET_EXCEEDED")

        prepared: list[tuple[Path, str, bytes | None, bytes, str]] = []
        total_bytes = 0
        seen: set[str] = set()
        for mutation in request.file_mutations:
            target, relative = _bounded_mutation_target(project_root, request, mutation.path)
            if relative in seen:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_DUPLICATE_PATH")
            seen.add(relative)
            if target.exists() and not target.is_file():
                raise RuntimeError("NATIVE_BOUNDED_WRITE_TARGET_NOT_FILE")
            before = target.read_bytes() if target.exists() else None
            before_hash = _sha256_bytes(before) if before is not None else "ABSENT"
            if before_hash != mutation.expected_before_sha256:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_EXPECTED_BEFORE_MISMATCH")
            content = mutation.content.encode("utf-8")
            if _sha256_bytes(content) != mutation.content_sha256:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_CONTENT_HASH_MISMATCH")
            if before == content:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_NOOP_FORBIDDEN")
            total_bytes += len(content)
            if total_bytes > budget.max_bytes:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_BYTE_BUDGET_EXCEEDED")
            prepared.append((target, relative, before, content, mutation.content_sha256))

        temp_paths: list[Path] = []
        try:
            for target, _, _, content, _ in prepared:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    delete=False,
                    dir=target.parent,
                    prefix=f".{target.name}.palwakf-",
                    suffix=".tmp",
                ) as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temp_path = Path(handle.name)
                temp_paths.append(temp_path)
                os.replace(temp_path, target)
                temp_paths.remove(temp_path)

            changed: list[str] = []
            for target, relative, before, _, expected_after in prepared:
                after = target.read_bytes()
                if _sha256_bytes(after) != expected_after:
                    raise RuntimeError("NATIVE_BOUNDED_WRITE_POSTCONDITION_HASH_MISMATCH")
                if before != after:
                    changed.append(relative)
            expected_changed = sorted(relative for _, relative, before, content, _ in prepared if before != content)
            if sorted(changed) != expected_changed:
                raise RuntimeError("NATIVE_BOUNDED_WRITE_CHANGED_FILES_MISMATCH")
        except Exception:
            for temp_path in temp_paths:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
            for target, _, before, _, _ in prepared:
                if before is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(before)
            raise

        return {
            "provider_id": self.provider_id.value,
            "successful": True,
            "action_type": "NATIVE_BOUNDED_FILE_MUTATION",
            "files": len(prepared),
            "bytes": total_bytes,
            "observations": [{
                "objective": request.objective,
                "authorized_mutation_paths": sorted(seen),
                "git_mutation": "NONE",
                "network": "DENIED",
                "database": "DENIED",
                "self_authorization": "FORBIDDEN",
            }],
            "errors": [],
            "changed_files": sorted(changed),
            "process_success": True,
            "policy_success": True,
            "tool_execution_success": True,
            "objective_success": True,
            "postcondition_success": True,
            "tool_call_observed": True,
            "evidence": [{
                "type": "NATIVE_BOUNDED_WRITE_RECEIPT",
                "requested_paths": sorted(seen),
                "changed_files": sorted(changed),
                "preflight_before_first_write": "PASS",
                "content_hash_verification": "PASS",
                "rollback_on_failure": "ENFORCED",
                "git_mutation": "NONE",
            }],
        }


class HermesProvider(ExecutionProvider):
    provider_id = ProviderId.HERMES

    def __init__(self):
        self.command = os.getenv("PALWAKF_HERMES_COMMAND", "hermes")

    def _executable(self) -> str | None:
        return shutil.which(self.command)

    @staticmethod
    def _assert_certified_profile(exe: str) -> str:
        process = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = ((process.stdout or "") + "\n" + (process.stderr or "")).strip()
        required_markers = ("Hermes Agent v0.20.5", "f4df86fe")
        if process.returncode != 0 or not all(marker in output for marker in required_markers):
            raise RuntimeError("HERMES_CERTIFICATION_PROFILE_MISMATCH")
        return output[:1000]

    @staticmethod
    def _resolve_git_bash_path() -> str | None:
        """Resolve Hermes' Windows Git Bash dependency before env isolation.

        The adapter intentionally replaces LOCALAPPDATA/HOME for the child process.
        On native Windows, Hermes discovers its installer-managed Git Bash through
        the host LOCALAPPDATA (or HERMES_GIT_BASH_PATH). Resolve that dependency
        before isolation and pass only the executable path into the sanitized env.
        """
        if os.name != "nt":
            return None

        candidates: list[Path] = []
        custom = os.environ.get("HERMES_GIT_BASH_PATH")
        if custom:
            candidates.append(Path(custom))

        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            root = Path(local_appdata)
            candidates.extend([
                root / "hermes" / "git" / "bin" / "bash.exe",
                root / "hermes" / "git" / "usr" / "bin" / "bash.exe",
                root / "Programs" / "Git" / "bin" / "bash.exe",
            ])

        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Git" / "bin" / "bash.exe")
        program_files_x86 = os.environ.get("ProgramFiles(x86)")
        if program_files_x86:
            candidates.append(Path(program_files_x86) / "Git" / "bin" / "bash.exe")

        for candidate in candidates:
            try:
                if candidate.is_file():
                    return str(candidate.resolve())
            except OSError:
                continue

        found = shutil.which("bash")
        if found:
            candidate = Path(found)
            try:
                if candidate.is_file():
                    return str(candidate.resolve())
            except OSError:
                pass
        return None

    @staticmethod
    def _sanitized_environment(
        *,
        hermes_home: Path,
        snapshot_root: Path,
        git_bash_path: str | None = None,
    ) -> dict[str, str]:
        safe_passthrough = (
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "TEMP",
            "TMP",
            "PROCESSOR_ARCHITECTURE",
            "NUMBER_OF_PROCESSORS",
        )
        env = {
            key: value
            for key in safe_passthrough
            if (value := os.environ.get(key))
        }

        appdata = hermes_home / "appdata"
        localappdata = hermes_home / "localappdata"
        appdata.mkdir(parents=True, exist_ok=True)
        localappdata.mkdir(parents=True, exist_ok=True)

        env.update({
            "HERMES_HOME": str(hermes_home),
            "TERMINAL_CWD": str(snapshot_root),
            "HOME": str(hermes_home),
            "USERPROFILE": str(hermes_home),
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(localappdata),
            "PYTHONIOENCODING": "utf-8",
        })
        if git_bash_path:
            env["HERMES_GIT_BASH_PATH"] = git_bash_path
        drive, tail = os.path.splitdrive(str(hermes_home))
        if drive:
            env["HOMEDRIVE"] = drive
            env["HOMEPATH"] = tail or "\\"
        return env

    def health(self) -> dict[str, Any]:
        exe = self._executable()
        if not exe:
            return {
                "provider_id": self.provider_id.value,
                "discovered": False,
                "healthy": False,
                "certification": "NOT_CERTIFIED",
                "error": "HERMES_COMMAND_NOT_DISCOVERED",
                "adapter_modes": ["READ_ONLY_DIAGNOSTIC"],
                "operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
            }
        try:
            p = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10, check=False)
            return {
                "provider_id": self.provider_id.value,
                "discovered": True,
                "healthy": p.returncode == 0,
                "version_output": (p.stdout or p.stderr).strip()[:500],
                "certification": "EXTERNAL_CERTIFICATION_EVIDENCE_REQUIRED",
                "adapter_modes": ["READ_ONLY_DIAGNOSTIC"],
                "filesystem_policy": "DISPOSABLE_SNAPSHOT_FAIL_CLOSED",
                "network_policy": "MODEL_PROVIDER_LOOPBACK_ONLY_TOOL_NETWORK_DENIED",
                "operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
                "cancel_supported": False,
                "timeout_supported": True,
            }
        except Exception as error:
            return {
                "provider_id": self.provider_id.value,
                "discovered": True,
                "healthy": False,
                "certification": "NOT_CERTIFIED",
                "error": f"{type(error).__name__}: {error}",
                "adapter_modes": ["READ_ONLY_DIAGNOSTIC"],
                "operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
            }

    @staticmethod
    def _assert_loopback_ollama(endpoint: str) -> str:
        parsed = urlparse(endpoint)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or host not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError("HERMES_MODEL_ENDPOINT_MUST_BE_LOOPBACK")
        return endpoint.rstrip("/")

    @staticmethod
    def _snapshot_digest(snapshot_root: Path) -> dict[str, str]:
        digest: dict[str, str] = {}
        for path in sorted(snapshot_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(snapshot_root).as_posix()
            digest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest

    @staticmethod
    def _hermes_tool_names(hermes_home: Path) -> list[str]:
        names: list[str] = []
        for db_path in hermes_home.rglob("state.db"):
            try:
                connection = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True, timeout=1.0)
                connection.execute("PRAGMA query_only=ON")
                try:
                    tables = [
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    ]
                    for table in tables:
                        if not table.replace("_", "").isalnum():
                            continue
                        columns = [
                            row[1]
                            for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
                        ]
                        if "tool_name" in columns:
                            for (value,) in connection.execute(
                                f'SELECT tool_name FROM "{table}" WHERE tool_name IS NOT NULL'
                            ).fetchall():
                                if isinstance(value, str) and value.strip():
                                    names.append(value.strip())
                        if "tool_calls" in columns:
                            for (value,) in connection.execute(
                                f'SELECT tool_calls FROM "{table}" WHERE tool_calls IS NOT NULL'
                            ).fetchall():
                                if not value:
                                    continue
                                try:
                                    payload = json.loads(value) if isinstance(value, str) else value
                                except Exception:
                                    continue
                                if isinstance(payload, dict):
                                    payload = [payload]
                                if not isinstance(payload, list):
                                    continue
                                for item in payload:
                                    if not isinstance(item, dict):
                                        continue
                                    name = item.get("name")
                                    function = item.get("function")
                                    if not name and isinstance(function, dict):
                                        name = function.get("name")
                                    if isinstance(name, str) and name.strip():
                                        names.append(name.strip())
                finally:
                    connection.close()
            except Exception:
                continue
        return sorted(set(names))

    @staticmethod
    def _cleanup_ephemeral_tree(
        temp_root: Path,
        *,
        attempts: int = 30,
        delay_seconds: float = 0.2,
    ) -> tuple[bool, str | None, int]:
        """Remove a Hermes run tree with bounded Windows/SQLite quiescence.

        A just-exited Hermes process can briefly retain a Windows handle on
        HERMES_HOME/state.db. Cleanup is a governed postcondition: retry for a
        bounded period, then return a classified failure instead of masking the
        execution outcome with an unstructured PermissionError.
        """
        last_error: str | None = None
        for attempt in range(1, attempts + 1):
            try:
                shutil.rmtree(temp_root)
                return True, None, attempt
            except FileNotFoundError:
                return True, None, attempt
            except OSError as error:
                last_error = f"{type(error).__name__}: {error}"
                if attempt < attempts:
                    time.sleep(delay_seconds)
        return False, last_error, attempts

    def execute_read_only(self, *, project_root: Path, request: RunRequest) -> dict[str, Any]:
        if request.provider_mode != "READ_ONLY_DIAGNOSTIC":
            raise RuntimeError("HERMES_ADAPTER_MODE_NOT_ADMITTED")
        if request.model_provider != "ollama" or not request.model_id:
            raise RuntimeError("HERMES_ADAPTER_REQUIRES_OLLAMA_MODEL")
        if request.environment.filesystem_policy.mode != "READ_ONLY" or not request.authorization.read_only:
            raise RuntimeError("HERMES_OPERATIONAL_WRITE_ADMISSION_CLOSED")
        if request.environment.network_policy.read or request.environment.network_policy.write:
            raise RuntimeError("HERMES_TOOL_NETWORK_MUST_REMAIN_DENIED")

        exe = self._executable()
        if not exe:
            raise RuntimeError("HERMES_COMMAND_NOT_DISCOVERED")
        certified_version = self._assert_certified_profile(exe)
        git_bash_path = self._resolve_git_bash_path()
        if os.name == "nt" and not git_bash_path:
            raise RuntimeError("HERMES_GIT_BASH_NOT_DISCOVERED_IN_HOST_ENVIRONMENT")

        ollama_endpoint = self._assert_loopback_ollama(
            os.getenv("PALWAKF_OLLAMA_ENDPOINT") or "http://127.0.0.1:11434"
        )
        files, bytes_seen = _authorized_files(project_root, request)
        timeout = request.environment.resource_budget.timeout_seconds
        sentinel = (request.required_output_sentinel or "").strip()
        if not sentinel:
            raise RuntimeError("HERMES_SEMANTIC_SUCCESS_SENTINEL_REQUIRED")
        if len(sentinel) > 128 or "\n" in sentinel or "\r" in sentinel:
            raise RuntimeError("HERMES_SEMANTIC_SUCCESS_SENTINEL_INVALID")

        temp_root = Path(tempfile.mkdtemp(prefix="palwakf-hermes-adapter-"))
        result: dict[str, Any] | None = None
        cleanup_ok = False
        cleanup_error: str | None = None
        cleanup_attempts = 0

        try:
            snapshot_root = temp_root / "workspace"
            hermes_home = temp_root / "hermes-home"
            snapshot_root.mkdir(parents=True, exist_ok=True)
            hermes_home.mkdir(parents=True, exist_ok=True)

            for source, relative, _ in files:
                target = snapshot_root / Path(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            before = self._snapshot_digest(snapshot_root)
            provider_name = "palwakf-ollama-adapter"
            config = {
                "custom_providers": [{
                    "name": provider_name,
                    "base_url": f"{ollama_endpoint}/v1",
                    "api_key": "ollama",
                    "model": request.model_id,
                    "api_mode": "chat_completions",
                    "extra_body": {"tool_choice": "auto"},
                }],
                "model": {
                    "default": request.model_id,
                    "provider": f"custom:{provider_name}",
                    "base_url": f"{ollama_endpoint}/v1",
                    "api_key": "ollama",
                },
                "terminal": {
                    "backend": "local",
                    "cwd": str(snapshot_root),
                    "timeout": timeout,
                },
                "agent": {
                    "max_turns": 6,
                    "tool_use_enforcement": True,
                },
            }
            (hermes_home / "config.yaml").write_text(
                yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            prompt = (
                "PALWAKF GOVERNED READ-ONLY EXECUTION. "
                "The workspace is a disposable read-only-admission snapshot. "
                "Use read_file when file inspection is needed. "
                "Do not call write_file, patch, terminal, execute_code, web, browser, "
                "git mutation, package installation, or any network tool. "
                "Do not create, modify, rename, or delete files. "
                f"Objective: {request.objective}. "
                "Only after the objective succeeds, output the exact success sentinel "
                f"on its own line: {sentinel}. "
                "Never output the success sentinel when the objective fails."
            )
            env = self._sanitized_environment(
                hermes_home=hermes_home,
                snapshot_root=snapshot_root,
                git_bash_path=git_bash_path,
            )

            command = [
                exe,
                "--in", str(snapshot_root),
                "--no-restore-cwd",
                "-t", "file",
                "-m", request.model_id,
                "-z", prompt,
            ]
            started = time.perf_counter()
            try:
                process = subprocess.run(
                    command,
                    cwd=hermes_home,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                timed_out = False
                return_code = process.returncode
                stdout = process.stdout or ""
                stderr = process.stderr or ""
            except subprocess.TimeoutExpired as error:
                timed_out = True
                return_code = -1
                stdout = error.stdout if isinstance(error.stdout, str) else ""
                stderr = error.stderr if isinstance(error.stderr, str) else ""

            after = self._snapshot_digest(snapshot_root)
            changed = sorted(
                path for path in set(before) | set(after)
                if before.get(path) != after.get(path)
            )
            tool_names = self._hermes_tool_names(hermes_home)
            unexpected_tools = sorted(set(tool_names) - {"read_file"})
            read_file_required = "read_file" in request.tools
            read_file_observed = "read_file" in tool_names
            stdout_lines = {line.strip() for line in stdout.splitlines() if line.strip()}
            objective_success = sentinel in stdout_lines
            process_success = (
                return_code == 0
                and not timed_out
            )
            policy_success = (
                not changed
                and not unexpected_tools
            )
            tool_execution_success = (
                not read_file_required
                or read_file_observed
            )
            postcondition_success = not changed
            successful = all(
                (
                    process_success,
                    policy_success,
                    tool_execution_success,
                    objective_success,
                    postcondition_success,
                )
            )
            errors: list[dict[str, Any]] = []
            if timed_out:
                errors.append({"code": "HERMES_TIMEOUT"})
            if return_code != 0:
                errors.append({"code": "HERMES_PROCESS_EXIT_NONZERO", "return_code": return_code})
            if changed:
                errors.append({"code": "HERMES_READ_ONLY_SNAPSHOT_MUTATION_DETECTED", "files": changed})
            if unexpected_tools:
                errors.append({"code": "HERMES_READ_ONLY_TOOL_POLICY_VIOLATION", "tools": unexpected_tools})
            if read_file_required and not read_file_observed:
                errors.append({"code": "HERMES_REQUIRED_READ_FILE_NOT_OBSERVED"})
            if not objective_success:
                errors.append({"code": "HERMES_OBJECTIVE_SENTINEL_NOT_OBSERVED"})

            result = {
                "provider_id": self.provider_id.value,
                "successful": successful,
                "action_type": "HERMES_READ_ONLY_EXECUTION",
                "files": len(files),
                "bytes": bytes_seen,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "return_code": return_code,
                "timed_out": timed_out,
                "stdout": stdout[:20_000],
                "stderr": stderr[:10_000],
                "observations": [{
                    "objective": request.objective,
                    "snapshot_files": len(files),
                    "snapshot_bytes": bytes_seen,
                    "source_project_mutation_surface": "NONE_DISPOSABLE_SNAPSHOT_ONLY",
                    "operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
                    "execution_admission": "CERTIFICATION_ONLY_NON_OPERATIONAL",
                    "certified_hermes_profile": certified_version,
                    "provider_process_cwd": str(hermes_home),
                    "file_tool_workspace_cwd": str(snapshot_root),
                    "git_bash_bridge": "PRESENT" if git_bash_path else "NOT_APPLICABLE",
                    "git_bash_path": git_bash_path,
                }],
                "errors": errors,
                "changed_files": [],
                "snapshot_changed_files": changed,
                "tool_names": tool_names,
                "unexpected_tools": unexpected_tools,
                "read_file_observed": read_file_observed,
                "process_success": process_success,
                "policy_success": policy_success,
                "tool_execution_success": tool_execution_success,
                "objective_success": objective_success,
                "postcondition_success": postcondition_success,
                "tool_call_observed": bool(tool_names),
                "semantic_verification_method": "OUTPUT_SENTINEL_EXACT_LINE",
                "evidence": [{
                    "type": "HERMES_ADAPTER_EXECUTION_SUMMARY",
                    "return_code": return_code,
                    "timed_out": timed_out,
                    "snapshot_changed_files": changed,
                    "tool_names": tool_names,
                    "unexpected_tools": unexpected_tools,
                    "certified_hermes_profile": certified_version,
                    "environment_keys": sorted(env.keys()),
                    "provider_process_cwd": str(hermes_home),
                    "file_tool_workspace_cwd": str(snapshot_root),
                    "git_bash_bridge": "PRESENT" if git_bash_path else "NOT_APPLICABLE",
                    "git_bash_path": git_bash_path,
                    "objective_success": objective_success,
                    "semantic_verification_method": "OUTPUT_SENTINEL_EXACT_LINE",
                    "sentinel_sha256": hashlib.sha256(sentinel.encode("utf-8")).hexdigest(),
                }],
            }
        finally:
            cleanup_ok, cleanup_error, cleanup_attempts = self._cleanup_ephemeral_tree(temp_root)

        if result is None:
            raise RuntimeError("HERMES_EXECUTION_RESULT_NOT_PRODUCED")

        result["ephemeral_cleanup"] = "PASS" if cleanup_ok else "FAIL_CLOSED"
        result["ephemeral_cleanup_attempts"] = cleanup_attempts
        result["evidence"][0]["ephemeral_cleanup"] = result["ephemeral_cleanup"]
        result["evidence"][0]["ephemeral_cleanup_attempts"] = cleanup_attempts

        if not cleanup_ok:
            result["errors"].append({
                "code": "HERMES_EPHEMERAL_CLEANUP_FAILED",
                "detail": cleanup_error,
                "path": str(temp_root),
            })
            result["evidence"][0]["cleanup_failure_path"] = str(temp_root)

        result["postcondition_success"] = bool(
            result.get("postcondition_success")
        ) and cleanup_ok

        result["successful"] = all(
            bool(result.get(key))
            for key in (
                "process_success",
                "policy_success",
                "tool_execution_success",
                "objective_success",
                "postcondition_success",
            )
        )

        return result
