from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import stat
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import ProviderId, RunReceipt, RunRequest
from .registry_projection import build_projection


class AuthorityError(RuntimeError):
    pass


class RunControl:
    """Cooperative cancellation signal for bounded runtime work."""

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self.reason = "EXTERNAL_CANCEL_REQUEST"

    def cancel(self, reason: str = "EXTERNAL_CANCEL_REQUEST") -> None:
        self.reason = reason or "EXTERNAL_CANCEL_REQUEST"
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AgenticRuntime:
    CHECKPOINT_SCHEMA = "palwakf.agentic.runtime.checkpoint.v1"
    def __init__(
        self,
        project_root: Path,
        source_commit_sha: str,
        *,
        target_project_root: Path | None = None,
        target_expected_head: str | None = None,
        clock: Callable[[], float] | None = None,
    ):
        self.project_root = project_root.resolve()
        self.source_commit_sha = source_commit_sha
        self.target_project_root = (target_project_root or project_root).resolve()
        self.target_expected_head = target_expected_head or source_commit_sha
        self.receipts: dict[str, RunReceipt] = {}
        self._clock = clock or time.monotonic
        self.evidence_root = Path(
            os.getenv(
                "PALWAKF_AGENTIC_EVIDENCE_ROOT",
                str(
                    Path(tempfile.gettempdir())
                    / "palwakf_agentic_ai_evidence"
                ),
            )
        ).resolve()
        self.evidence_root.mkdir(parents=True, exist_ok=True)

    def _validate(self, request: RunRequest):
        auth = request.authorization
        env = request.environment
        if (
            request.project_id != auth.project_id
            or request.project_id != env.project_id
        ):
            raise AuthorityError("CROSS_PROJECT_ACCESS_DENIED")
        if request.task_id != auth.task_id:
            raise AuthorityError("TASK_AUTHORITY_MISMATCH")
        if request.agent_id not in auth.allowed_agent_ids:
            raise AuthorityError("AGENT_NOT_AUTHORIZED")
        if request.task_class not in auth.allowed_task_classes:
            raise AuthorityError("TASK_CLASS_NOT_AUTHORIZED")
        if request.provider_id not in auth.allowed_provider_ids:
            raise AuthorityError("PROVIDER_NOT_AUTHORIZED")
        if request.model_provider not in auth.allowed_model_providers:
            raise AuthorityError("MODEL_PROVIDER_NOT_AUTHORIZED")
        if not auth.read_only or env.filesystem_policy.mode != "READ_ONLY":
            raise AuthorityError("WRITE_REQUIRES_SEPARATE_AUTHORITY")
        if auth.allow_network_write or env.network_policy.write:
            raise AuthorityError("NETWORK_WRITE_DENIED")
        if (
            env.filesystem_policy.allowed_patterns
            != auth.allowed_path_patterns
        ):
            raise AuthorityError("FILESYSTEM_PATTERN_AUTHORITY_MISMATCH")
        if not env.filesystem_policy.allowed_patterns:
            raise AuthorityError("FILESYSTEM_PATTERN_REQUIRED")
        # base_sha is the historical task base. expected_head belongs to the
        # independently bound target project, not to the Agentic runtime source.
        if env.expected_head != self.target_expected_head:
            raise AuthorityError("SOURCE_SHA_MISMATCH")

        agents = {
            agent.agent_id: agent
            for agent in build_projection(
                self.project_root,
                self.source_commit_sha,
            )
        }
        agent = agents.get(request.agent_id)
        if agent is None:
            raise AuthorityError("AGENT_NOT_REGISTERED")
        if not agent.runnable:
            raise AuthorityError("NOT_RUNNABLE_FAIL_CLOSED")
        if agent.role_id != request.role_id:
            raise AuthorityError("ROLE_AGENT_MISMATCH")
        if request.task_class not in agent.allowed_task_classes:
            raise AuthorityError("AGENT_TASK_CLASS_NOT_ALLOWED")
        if not set(request.skill_ids).issubset(set(agent.skill_ids)):
            raise AuthorityError("SKILL_SCOPE_EXPANSION_DENIED")

        worktree = Path(env.worktree).resolve()
        if worktree != self.target_project_root:
            raise AuthorityError("WORKTREE_MISMATCH")
        for root in auth.allowed_filesystem_roots:
            resolved = Path(root).resolve()
            if (
                resolved != self.target_project_root
                and not _is_within(
                    resolved,
                    self.target_project_root,
                )
            ):
                raise AuthorityError("AUTHORIZED_ROOT_OUTSIDE_PROJECT")
        return agent

    @staticmethod
    def _binding_fingerprint(request: RunRequest) -> str:
        return _canonical_sha256(request.model_dump(mode="json"))

    def _checkpoint_path(self, run_id: str) -> Path:
        return self.evidence_root / f"{run_id}.checkpoint.json"

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    def _write_checkpoint(
        self,
        *,
        run_id: str,
        request: RunRequest,
        status: str,
        next_index: int,
        manifest: list[dict[str, Any]],
        bytes_seen: int,
        retries: int,
        error: dict[str, Any] | None = None,
        resumed_from_run_id: str | None = None,
    ) -> Path:
        path = self._checkpoint_path(run_id)
        payload: dict[str, Any] = {
            "schema": self.CHECKPOINT_SCHEMA,
            "run_id": run_id,
            "status": status,
            "binding_fingerprint": self._binding_fingerprint(request),
            "next_index": next_index,
            "manifest": manifest,
            "bytes_seen": bytes_seen,
            "retries": retries,
            "error": error,
            "resumed_from_run_id": resumed_from_run_id,
        }
        self._write_json_atomic(path, payload)
        return path

    def _load_checkpoint(
        self,
        request: RunRequest,
        checkpoint_path: Path | str,
    ) -> dict[str, Any]:
        path = Path(checkpoint_path).resolve()
        if not _is_within(path, self.evidence_root):
            raise AuthorityError(
                "RESUME_CHECKPOINT_OUTSIDE_EVIDENCE_ROOT"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AuthorityError(
                "RESUME_CHECKPOINT_UNREADABLE"
            ) from error
        if payload.get("schema") != self.CHECKPOINT_SCHEMA:
            raise AuthorityError("RESUME_CHECKPOINT_SCHEMA_MISMATCH")
        if (
            payload.get("binding_fingerprint")
            != self._binding_fingerprint(request)
        ):
            raise AuthorityError("RESUME_BINDING_MISMATCH")
        if payload.get("status") not in {
            "CANCELLED",
            "TIMED_OUT",
            "FAILED_RETRYABLE",
        }:
            raise AuthorityError("RESUME_CHECKPOINT_NOT_RESUMABLE")
        if not isinstance(payload.get("manifest"), list):
            raise AuthorityError("RESUME_CHECKPOINT_MANIFEST_INVALID")
        if not isinstance(payload.get("next_index"), int):
            raise AuthorityError("RESUME_CHECKPOINT_INDEX_INVALID")
        return payload
    def _candidate_paths(
        self,
        patterns: list[str],
    ) -> list[tuple[str, Path]]:
        candidates: list[tuple[str, Path]] = []
        for path in self.target_project_root.rglob("*"):
            if (
                ".git" in path.parts
                or ".palwakf_apply_backup" in path.parts
            ):
                continue
            relative = path.relative_to(
                self.target_project_root
            ).as_posix()
            if not any(
                fnmatch.fnmatchcase(relative, pattern)
                for pattern in patterns
            ):
                continue
            candidates.append((relative, path))
        return sorted(candidates, key=lambda item: item[0])

    @staticmethod
    def _stat_file(path: Path):
        return path.stat()

    def _stat_with_retry(
        self,
        path: Path,
        *,
        max_retries: int,
    ) -> tuple[os.stat_result, int]:
        retries = 0
        while True:
            try:
                return self._stat_file(path), retries
            except OSError:
                if retries >= max_retries:
                    raise
                retries += 1

    def _persist_receipt(self, receipt: RunReceipt) -> RunReceipt:
        self.receipts[receipt.run_id] = receipt
        path = self.evidence_root / f"{receipt.run_id}.json"
        receipt.evidence.append(
            {"type": "RUN_RECEIPT_JSON", "path": str(path)}
        )
        path.write_text(
            receipt.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return receipt

    def _interrupted_receipt(
        self,
        *,
        request: RunRequest,
        run_id: str,
        final_result: str,
        error_code: str,
        error_message: str,
        manifest: list[dict[str, Any]],
        bytes_seen: int,
        retries: int,
        next_index: int,
        resumed_from_run_id: str | None,
    ) -> RunReceipt:
        checkpoint = self._write_checkpoint(
            run_id=run_id,
            request=request,
            status=final_result,
            next_index=next_index,
            manifest=manifest,
            bytes_seen=bytes_seen,
            retries=retries,
            error={"code": error_code, "message": error_message},
            resumed_from_run_id=resumed_from_run_id,
        )
        receipt = self._base_receipt(
            request=request,
            run_id=run_id,
            manifest=manifest,
            bytes_seen=bytes_seen,
            retries=retries,
            final_result=final_result,
            next_action="RESUME_REQUIRES_SAME_AUTHORITY_AND_BINDING",
            errors=[
                {"code": error_code, "message": error_message}
            ],
            resumed_from_run_id=resumed_from_run_id,
        )
        receipt.evidence.append(
            {"type": "RUN_CHECKPOINT_JSON", "path": str(checkpoint)}
        )
        return self._persist_receipt(receipt)

    def _base_receipt(
        self,
        *,
        request: RunRequest,
        run_id: str,
        manifest: list[dict[str, Any]],
        bytes_seen: int,
        retries: int,
        final_result: str,
        next_action: str,
        errors: list[dict[str, Any]],
        resumed_from_run_id: str | None,
    ) -> RunReceipt:
        observations: list[dict[str, Any]] = [
            {
                "manifest_sample": manifest[:50],
                "objective": request.objective,
            }
        ]
        if resumed_from_run_id:
            observations.append(
                {
                    "resume_from_run_id": resumed_from_run_id,
                    "resume_binding_verified": True,
                }
            )
        return RunReceipt(
            run_id=run_id,
            project_id=request.project_id,
            task_id=request.task_id,
            state_package_id=request.state_package_id,
            agent_id=request.agent_id,
            role_id=request.role_id,
            skill_ids=request.skill_ids,
            provider_id=request.provider_id,
            provider_mode=request.provider_mode,
            model_provider=request.model_provider,
            model_id=request.model_id,
            tools=request.tools,
            environment=request.environment.model_dump(),
            base_sha=request.environment.base_sha,
            before_head=request.environment.expected_head,
            authorized_scope=request.authorization.model_dump(
                mode="json"
            ),
            plan=[
                "validate_external_authority",
                "resolve_agent",
                "resolve_provider",
                "run_bounded_read_only_diagnostic",
                "emit_receipt",
            ],
            actions=[
                {
                    "type": "READ_ONLY_REPOSITORY_MANIFEST",
                    "files": len(manifest),
                    "bytes": bytes_seen,
                }
            ],
            observations=observations,
            changed_files=[],
            tests=[],
            errors=errors,
            retries=retries,
            evidence=[],
            final_result=final_result,
            next_action=next_action,
        )

    def execute(
        self,
        request: RunRequest,
        *,
        control: RunControl | None = None,
        resume_checkpoint: Path | str | None = None,
    ) -> RunReceipt:
        self._validate(request)
        if request.provider_id != ProviderId.NATIVE:
            raise AuthorityError("HERMES_NOT_CERTIFIED_FOR_EXECUTION")

        budget = request.environment.resource_budget
        control = control or RunControl()
        run_id = f"run-{uuid4()}"
        manifest: list[dict[str, Any]] = []
        bytes_seen = 0
        retries = 0
        next_index = 0
        resumed_from_run_id: str | None = None

        if resume_checkpoint is not None:
            checkpoint = self._load_checkpoint(
                request,
                resume_checkpoint,
            )
            manifest = list(checkpoint["manifest"])
            bytes_seen = int(checkpoint.get("bytes_seen") or 0)
            retries = int(checkpoint.get("retries") or 0)
            next_index = int(checkpoint["next_index"])
            resumed_from_run_id = str(
                checkpoint.get("run_id") or ""
            ) or None

        started = self._clock()
        patterns = request.environment.filesystem_policy.allowed_patterns
        candidates = self._candidate_paths(patterns)
        if next_index < 0 or next_index > len(candidates):
            raise AuthorityError("RESUME_CHECKPOINT_INDEX_OUT_OF_RANGE")

        for index in range(next_index, len(candidates)):
            if control.cancelled:
                return self._interrupted_receipt(
                    request=request,
                    run_id=run_id,
                    final_result="CANCELLED",
                    error_code="RUN_CANCELLED",
                    error_message=control.reason,
                    manifest=manifest,
                    bytes_seen=bytes_seen,
                    retries=retries,
                    next_index=index,
                    resumed_from_run_id=resumed_from_run_id,
                )

            if self._clock() - started >= budget.timeout_seconds:
                return self._interrupted_receipt(
                    request=request,
                    run_id=run_id,
                    final_result="TIMED_OUT",
                    error_code="RUN_TIMEOUT",
                    error_message=(
                        "RESOURCE_BUDGET_TIMEOUT_SECONDS_EXCEEDED"
                    ),
                    manifest=manifest,
                    bytes_seen=bytes_seen,
                    retries=retries,
                    next_index=index,
                    resumed_from_run_id=resumed_from_run_id,
                )

            if len(manifest) >= budget.max_files:
                break

            relative, path = candidates[index]
            try:
                file_stat, file_retries = self._stat_with_retry(
                    path,
                    max_retries=budget.max_retries,
                )
            except OSError as error:
                return self._interrupted_receipt(
                    request=request,
                    run_id=run_id,
                    final_result="FAILED_RETRYABLE",
                    error_code="FILE_STAT_RETRY_EXHAUSTED",
                    error_message=f"{type(error).__name__}: {error}",
                    manifest=manifest,
                    bytes_seen=bytes_seen,
                    retries=retries + budget.max_retries,
                    next_index=index,
                    resumed_from_run_id=resumed_from_run_id,
                )

            retries += file_retries
            if not stat.S_ISREG(file_stat.st_mode):
                continue
            size = int(file_stat.st_size)
            if bytes_seen + size > budget.max_bytes:
                break
            bytes_seen += size
            manifest.append({"path": relative, "size": size})

        receipt = self._base_receipt(
            request=request,
            run_id=run_id,
            manifest=manifest,
            bytes_seen=bytes_seen,
            retries=retries,
            final_result="PASS",
            next_action="EXTERNAL_REVIEW_REQUIRED",
            errors=[],
            resumed_from_run_id=resumed_from_run_id,
        )
        return self._persist_receipt(receipt)
