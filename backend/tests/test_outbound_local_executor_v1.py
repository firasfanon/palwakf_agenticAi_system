from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityDescriptorV1,
    CapabilityRegistryV1,
    default_capability_registry_v1,
)
from palwakf_local_agents.outbound_contracts_v1 import (
    AuthorityProofV1,
    Ed25519AuthorityVerifierV1,
    ExecutionLeaseV1,
    TaskEnvelopeV1,
)
from palwakf_local_agents.outbound_local_executor_v1 import ExecutorSettingsV1, PalWakfOutboundLocalExecutorV1


BASE = "56dbad6e266fe765a6f43fe642ee53a885a04821"
BRANCH = "task/AGENTIC-P3-OUTBOUND-LOCAL-EXECUTOR-V1"


def keys():
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes_raw()
    return private, base64.b64encode(public_raw).decode()


def envelope(
    tmp_path: Path,
    private: Ed25519PrivateKey,
    capability="mesh_hostname",
    mutation="READ_ONLY",
    arguments=None,
    idem="idem-00000001",
    repository_id="firasfanon/palwakf_agenticAi_system",
):
    now = datetime.now(UTC)
    lease = ExecutionLeaseV1(
        lease_id="lease-outbound-v1",
        task_id="task-outbound-v1",
        project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        issuer_ref="workspace://execution-lease/1",
        approval_class="IMPLEMENTATION",
        allowed_capability_ids=(capability,),
        allowed_mutation_classes=(mutation,),
        scope_paths=(str(tmp_path),) if mutation != "READ_ONLY" else (),
        base_sha=BASE,
        branch=BRANCH,
        issued_at=now,
        expires_at=now + timedelta(minutes=20),
    )
    unsigned = TaskEnvelopeV1.model_construct(
        contract_version="1.0", task_id="task-outbound-v1", project_id="PALWAKF_AGENTIC_AI_SYSTEM",
        project_aliases=(), repository_id=repository_id, executor_id="Futuer-IT",
        task_type="READ_ONLY_PROOF", mutation_class=mutation, requested_capability_id=capability,
        arguments=arguments or {}, authority_ref="workspace://authority/1", execution_lease=lease,
        expected_remote_head=BASE, expected_base_sha=BASE, task_branch=BRANCH,
        scope_paths=(str(tmp_path),) if mutation != "READ_ONLY" else (), prohibited_actions=("main_merge",),
        idempotency_key=idem, nonce="nonce-00000001", issued_at=now, expires_at=now + timedelta(minutes=10),
        max_duration_seconds=120, evidence_requirements=("evidence",), transport_metadata={},
        authority_proof=AuthorityProofV1(key_id="k1", signature_b64=base64.b64encode(b"0"*64).decode()),
        correlation_id=None, checkpoint_id=None, depends_on_task_ids=(), model_provider_metadata={}
    )
    sig = private.sign(unsigned.canonical_bytes())
    data = unsigned.model_dump(mode="python")
    data["authority_proof"] = {"algorithm":"ED25519","key_id":"k1","signature_b64":base64.b64encode(sig).decode()}
    return TaskEnvelopeV1.model_validate(data)


def executor(
    tmp_path: Path,
    public_b64: str,
    allowed_repository_ids: tuple[str, ...] = (),
):
    settings = ExecutorSettingsV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/palwakf_agenticAi_system",
        allowed_repository_ids=allowed_repository_ids,
        allowed_roots=(str(tmp_path),),
        state_dir=str(tmp_path / "state"),
    )
    return PalWakfOutboundLocalExecutorV1(
        settings=settings,
        authority_verifier=Ed25519AuthorityVerifierV1({"k1": public_b64}),
        registry=default_capability_registry_v1(),
    )


def test_signed_hostname_executes_and_emits_zero_manual_evidence(tmp_path):
    private, public = keys()
    ev = executor(tmp_path, public).execute(envelope(tmp_path, private), transport_adapter="github-issues-v1")
    assert ev.exit_state == "COMPLETED"
    assert ev.authority_verdict == "PASS"
    assert ev.manual_terminal_interventions_per_task == 0
    assert ev.arbitrary_shell_exposed is False
    assert ev.artifact_hashes == ()
    assert ev.checkpoint_ref is None


def test_signature_tamper_is_rejected(tmp_path):
    private, public = keys()
    env = envelope(tmp_path, private)
    data = env.model_dump(mode="python")
    data["arguments"] = {"tampered": True}
    tampered = TaskEnvelopeV1.model_validate(data)
    ev = executor(tmp_path, public).execute(tampered, transport_adapter="github-issues-v1")
    assert ev.exit_state == "REJECTED"
    assert "AUTHORITY_SIGNATURE_INVALID" in ev.blockers


def test_idempotency_returns_existing_evidence_without_duplicate_execution(tmp_path):
    private, public = keys()
    exe = executor(tmp_path, public)
    env = envelope(tmp_path, private)
    first = exe.execute(env, transport_adapter="github-issues-v1")
    second = exe.execute(env, transport_adapter="github-issues-v1")
    assert first.model_dump() == second.model_dump()


def test_unknown_legacy_write_capability_fails_closed(tmp_path):
    private, public = keys()
    env = envelope(tmp_path, private, capability="bounded_powershell")
    ev = executor(tmp_path, public).execute(env, transport_adapter="github-issues-v1")
    assert ev.exit_state == "BLOCKED"


def test_wrong_expected_head_is_rejected_by_authority_verifier(tmp_path):
    private, public = keys()
    env = envelope(tmp_path, private)
    data = env.model_dump(mode="python")
    data["expected_remote_head"] = "1" * 40
    unsigned = TaskEnvelopeV1.model_validate(data)
    sig = private.sign(unsigned.canonical_bytes())
    data["authority_proof"]["signature_b64"] = base64.b64encode(sig).decode()
    drifted = TaskEnvelopeV1.model_validate(data)
    ev = executor(tmp_path, public).execute(drifted, transport_adapter="github-issues-v1")
    assert ev.exit_state == "REJECTED"
    assert "EXPECTED_REMOTE_HEAD_DRIFT" in ev.blockers


def test_allowlisted_secondary_repository_executes(tmp_path):
    private, public = keys()
    repository = "firasfanon/palwakf_mind_assistant"
    exe = executor(tmp_path, public, allowed_repository_ids=(repository,))
    env = envelope(
        tmp_path,
        private,
        repository_id=repository,
        idem="idem-secondary-repo-01",
    )
    evidence = exe.execute(env, transport_adapter="workspace-drive-remote-intent-v1")
    assert evidence.exit_state == "COMPLETED"
    assert evidence.authority_verdict == "PASS"


def test_non_allowlisted_repository_is_rejected(tmp_path):
    private, public = keys()
    repository = "firasfanon/not-allowed"
    env = envelope(
        tmp_path,
        private,
        repository_id=repository,
        idem="idem-rejected-repo-01",
    )
    evidence = executor(tmp_path, public).execute(
        env,
        transport_adapter="workspace-drive-remote-intent-v1",
    )
    assert evidence.exit_state == "REJECTED"
    assert "REPOSITORY_ID_MISMATCH" in evidence.blockers


def test_codex_proposal_is_persisted_as_local_hashed_artifact(tmp_path):
    private, public = keys()

    def proposal_handler(_ctx, _args):
        return {
            "provider": "codex-cli",
            "mode": "READ_ONLY_PATCH_PROPOSAL",
            "before_head": BASE,
            "changed_files": ["docs/uat.md"],
            "unified_diff": "--- /dev/null\n+++ b/docs/uat.md\n@@ -0,0 +1 @@\n+uat\n",
            "summary": "proposal",
            "tests": [],
            "git_mutation_allowed": False,
        }

    registry = CapabilityRegistryV1(
        (
            CapabilityDescriptorV1(
                "engineering.codex.patch_proposal",
                "READ_ONLY",
                proposal_handler,
            ),
        )
    )
    settings = ExecutorSettingsV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/palwakf_agenticAi_system",
        allowed_roots=(str(tmp_path),),
        state_dir=str(tmp_path / "state"),
    )
    exe = PalWakfOutboundLocalExecutorV1(
        settings=settings,
        authority_verifier=Ed25519AuthorityVerifierV1({"k1": public}),
        registry=registry,
    )
    env = envelope(
        tmp_path,
        private,
        capability="engineering.codex.patch_proposal",
        mutation="READ_ONLY",
        idem="idem-codex-artifact-01",
    )
    evidence = exe.execute(
        env,
        transport_adapter="workspace-drive-remote-intent-v1",
    )

    assert evidence.exit_state == "COMPLETED"
    assert len(evidence.artifact_hashes) == 1
    assert evidence.checkpoint_ref is not None
    prefix = "local-result://"
    assert evidence.checkpoint_ref.startswith(prefix)
    artifact_id, ref_hash = evidence.checkpoint_ref[len(prefix):].split("/")
    assert ref_hash == evidence.artifact_hashes[0]
    artifact_path = tmp_path / "state" / "capability-results" / f"{artifact_id}.json"
    data = artifact_path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ref_hash
    artifact = json.loads(data)
    assert artifact["capability_id"] == "engineering.codex.patch_proposal"
    assert artifact["result"]["git_mutation_allowed"] is False
    assert artifact["result"]["mode"] == "READ_ONLY_PATCH_PROPOSAL"
