from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .contracts import ProviderId, RunReceipt, RunRequest
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
    def __init__(self, project_root: Path, source_commit_sha: str):
        self.project_root = project_root.resolve()
        self.source_commit_sha = source_commit_sha
        self.receipts: dict[str, RunReceipt] = {}
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
        if not auth.read_only or env.filesystem_policy.mode != "READ_ONLY":
            raise AuthorityError("WRITE_REQUIRES_SEPARATE_AUTHORITY")
        if auth.allow_network_write or env.network_policy.write:
            raise AuthorityError("NETWORK_WRITE_DENIED")
        if env.base_sha != self.source_commit_sha or env.expected_head != self.source_commit_sha:
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

        worktree = Path(env.worktree).resolve()
        if worktree != self.project_root:
            raise AuthorityError("WORKTREE_MISMATCH")
        for root in auth.allowed_filesystem_roots:
            rp = Path(root).resolve()
            if rp != self.project_root and not _is_within(rp, self.project_root):
                raise AuthorityError("AUTHORIZED_ROOT_OUTSIDE_PROJECT")
        return agent

    def execute(self, request: RunRequest) -> RunReceipt:
        self._validate(request)
        if request.provider_id != ProviderId.NATIVE:
            raise AuthorityError("HERMES_NOT_CERTIFIED_FOR_EXECUTION")

        budget = request.environment.resource_budget
        manifest = []
        bytes_seen = 0
        for path in self.project_root.rglob("*"):
            if len(manifest) >= budget.max_files:
                break
            if ".git" in path.parts or not path.is_file():
                continue
            size = path.stat().st_size
            if bytes_seen + size > budget.max_bytes:
                break
            bytes_seen += size
            manifest.append({"path": path.relative_to(self.project_root).as_posix(), "size": size})

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
            plan=[
                "validate_external_authority",
                "resolve_agent",
                "resolve_provider",
                "run_bounded_read_only_diagnostic",
                "emit_receipt",
            ],
            actions=[{"type": "READ_ONLY_REPOSITORY_MANIFEST", "files": len(manifest), "bytes": bytes_seen}],
            observations=[{"manifest_sample": manifest[:50], "objective": request.objective}],
            changed_files=[],
            tests=[],
            errors=[],
            retries=0,
            evidence=[],
            final_result="PASS",
            next_action="EXTERNAL_REVIEW_REQUIRED",
        )
        self.receipts[receipt.run_id] = receipt
        p = self.evidence_root / f"{receipt.run_id}.json"
        receipt.evidence.append({"type": "RUN_RECEIPT_JSON", "path": str(p)})
        p.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
        return receipt
