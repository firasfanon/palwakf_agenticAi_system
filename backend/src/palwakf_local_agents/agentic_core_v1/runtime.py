from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from .contracts import ProviderId, RunReceipt, RunRequest
from .providers import ExecutionProvider, HermesProvider, NativeProvider
from .registry_projection import build_projection


class AuthorityError(RuntimeError):
    pass


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class AgenticRuntime:
    def __init__(
        self,
        project_root: Path,
        source_commit_sha: str,
        execution_providers: dict[ProviderId, ExecutionProvider] | None = None,
    ):
        self.project_root = project_root.resolve()
        self.source_commit_sha = source_commit_sha
        self.receipts: dict[str, RunReceipt] = {}
        self.execution_providers = execution_providers or {
            ProviderId.NATIVE: NativeProvider(),
            ProviderId.HERMES: HermesProvider(),
        }
        self.evidence_root = Path(os.getenv(
            "PALWAKF_AGENTIC_EVIDENCE_ROOT",
            str(Path(tempfile.gettempdir()) / "palwakf_agentic_ai_evidence"),
        ))
        self.evidence_root.mkdir(parents=True, exist_ok=True)

    def _validate(self, request: RunRequest):
        auth = request.authorization
        env = request.environment

        if request.project_id != auth.project_id or request.project_id != env.project_id:
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

        if len(set(request.tools)) != len(request.tools):
            raise AuthorityError("DUPLICATE_REQUEST_TOOL_DENIED")
        if len(set(env.tool_policy)) != len(env.tool_policy):
            raise AuthorityError("DUPLICATE_ENVIRONMENT_TOOL_DENIED")
        if set(request.tools) != set(env.tool_policy):
            raise AuthorityError("TOOL_POLICY_REQUEST_MISMATCH")
        if not set(request.tools).issubset(set(auth.allowed_tools)):
            raise AuthorityError("TOOL_NOT_AUTHORIZED")

        if not auth.read_only or env.filesystem_policy.mode != "READ_ONLY":
            raise AuthorityError("WRITE_REQUIRES_SEPARATE_AUTHORITY")
        if auth.allow_network_write or env.network_policy.write:
            raise AuthorityError("NETWORK_WRITE_DENIED")
        if env.filesystem_policy.allowed_patterns != auth.allowed_path_patterns:
            raise AuthorityError("FILESYSTEM_PATTERN_AUTHORITY_MISMATCH")
        if not env.filesystem_policy.allowed_patterns:
            raise AuthorityError("FILESYSTEM_PATTERN_REQUIRED")

        auth_roots = sorted(
            os.path.normcase(str(Path(root).resolve()))
            for root in auth.allowed_filesystem_roots
        )
        env_roots = sorted(
            os.path.normcase(str(Path(root).resolve()))
            for root in env.filesystem_policy.allowed_roots
        )
        if not auth_roots or not env_roots:
            raise AuthorityError("FILESYSTEM_ROOT_REQUIRED")
        if auth_roots != env_roots:
            raise AuthorityError("FILESYSTEM_ROOT_AUTHORITY_MISMATCH")
        # base_sha is the historical task base; expected_head is the currently
        # authorized remote/worktree head and must match the runtime source.
        if env.expected_head != self.source_commit_sha:
            raise AuthorityError("SOURCE_SHA_MISMATCH")

        agents = {a.agent_id: a for a in build_projection(self.project_root, self.source_commit_sha)}
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
        if request.provider_id not in agent.execution_provider_policy:
            raise AuthorityError("AGENT_PROVIDER_NOT_ALLOWED")

        worktree = Path(env.worktree).resolve()
        if worktree != self.project_root:
            raise AuthorityError("WORKTREE_MISMATCH")
        for root in auth.allowed_filesystem_roots:
            rp = Path(root).resolve()
            if rp != self.project_root and not _is_within(rp, self.project_root):
                raise AuthorityError("AUTHORIZED_ROOT_OUTSIDE_PROJECT")

        if request.provider_id == ProviderId.HERMES:
            if request.provider_mode != "READ_ONLY_DIAGNOSTIC":
                raise AuthorityError("HERMES_ADAPTER_MODE_NOT_ADMITTED")
            if request.model_provider != "ollama" or not request.model_id:
                raise AuthorityError("HERMES_ADAPTER_REQUIRES_OLLAMA_MODEL")
            if env.network_policy.read:
                raise AuthorityError("HERMES_TOOL_NETWORK_READ_DENIED")

            certification_authorization_id = os.getenv(
                "PALWAKF_HERMES_CERTIFICATION_AUTHORIZATION_ID",
                "",
            )
            if (
                auth.issuer != "HUMAN_EXPLICIT"
                or certification_authorization_id != auth.authorization_id
            ):
                raise AuthorityError("HERMES_OPERATIONAL_ADMISSION_CLOSED")
            if request.tools != ["read_file"] or env.tool_policy != ["read_file"]:
                raise AuthorityError("HERMES_CERTIFICATION_TOOL_POLICY_MUST_BE_READ_FILE_ONLY")
            if auth.allowed_tools != ["read_file"]:
                raise AuthorityError("HERMES_CERTIFICATION_AUTHORIZED_TOOLS_MUST_BE_READ_FILE_ONLY")

        return agent

    def execute(self, request: RunRequest) -> RunReceipt:
        self._validate(request)
        provider = self.execution_providers.get(request.provider_id)
        if provider is None:
            raise AuthorityError("EXECUTION_PROVIDER_NOT_REGISTERED")

        try:
            provider_result = provider.execute_read_only(
                project_root=self.project_root,
                request=request,
            )
        except Exception as error:
            provider_result = {
                "provider_id": request.provider_id.value,
                "successful": False,
                "action_type": "EXECUTION_PROVIDER_FAILURE",
                "observations": [{"objective": request.objective}],
                "errors": [{"code": str(error), "type": type(error).__name__}],
                "changed_files": [],
                "evidence": [],
            }

        successful = bool(provider_result.get("successful"))
        action: dict[str, Any] = {
            "type": provider_result.get("action_type", "EXECUTION_PROVIDER_RESULT"),
            "provider_id": request.provider_id.value,
        }
        for key in ("files", "bytes", "latency_ms", "return_code", "timed_out", "snapshot_changed_files", "tool_names", "unexpected_tools", "read_file_observed"):
            if key in provider_result:
                action[key] = provider_result[key]

        plan = [
            "validate_external_authority",
            "resolve_agent",
            "resolve_provider",
            (
                "execute_via_hermes_adapter_read_only"
                if request.provider_id == ProviderId.HERMES
                else "run_bounded_read_only_diagnostic"
            ),
            "emit_receipt",
        ]

        observations = list(provider_result.get("observations") or [])
        if request.provider_id == ProviderId.HERMES:
            observations.append({
                "hermes_operational_write_admission": "CLOSED_SEPARATE_GATE_REQUIRED",
                "source_workspace_mode": "DISPOSABLE_SNAPSHOT",
                "hermes_execution_admission": "CERTIFICATION_ONLY_NON_OPERATIONAL",
            })
            if provider_result.get("stdout"):
                observations.append({"hermes_stdout": provider_result["stdout"]})
            if provider_result.get("stderr"):
                observations.append({"hermes_stderr": provider_result["stderr"]})

        receipt = RunReceipt(
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
            authorized_scope=request.authorization.model_dump(mode="json"),
            plan=plan,
            actions=[action],
            observations=observations,
            changed_files=list(provider_result.get("changed_files") or []),
            tests=[],
            errors=list(provider_result.get("errors") or []),
            retries=0,
            evidence=list(provider_result.get("evidence") or []),
            final_result="PASS" if successful else "FAIL_CLOSED",
            next_action="EXTERNAL_REVIEW_REQUIRED",
        )
        self.receipts[receipt.run_id] = receipt
        p = self.evidence_root / f"{receipt.run_id}.json"
        receipt.evidence.append({"type": "RUN_RECEIPT_JSON", "path": str(p)})
        p.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
        return receipt
