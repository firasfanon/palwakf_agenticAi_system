from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from palwakf_local_agents.outbound_contracts_v1 import (
    Ed25519AuthorityVerifierV1,
    TaskEnvelopeV1,
)
from palwakf_local_agents.outbound_worker_v1 import WorkerConfigV1


def _config(path: Path | None) -> WorkerConfigV1:
    return WorkerConfigV1.model_validate(
        {
            "executor": {
                "executor_id": "Futuer-IT",
                "repository_id": "firasfanon/palwakf_agenticAi_system",
                "allowed_roots": [r"C:\repo"],
                "state_dir": r"C:\state",
            },
            "transport": {
                "repository": "firasfanon/palwakf_agenticAi_system",
                "task_label": "question",
                "token_env_var": "PALWAKF_GITHUB_TOKEN",
                "token_protected_path": None,
            },
            "authority_public_keys_b64": {
                "acceptance-r11": base64.b64encode(b"a" * 32).decode("ascii"),
            },
            "authority_public_keys_path": str(path) if path is not None else None,
        }
    )


def test_external_public_trust_store_merges_without_replacing_existing_key(
    tmp_path: Path,
) -> None:
    path = tmp_path / "authority-keys.json"
    rotated = base64.b64encode(b"b" * 32).decode("ascii")
    path.write_text(
        json.dumps({"workspace-c7r-v1": rotated}),
        encoding="utf-8",
    )

    keys = _config(path).effective_authority_public_keys()

    assert set(keys) == {"acceptance-r11", "workspace-c7r-v1"}
    assert keys["workspace-c7r-v1"] == rotated


def test_external_public_trust_store_rejects_key_id_conflict(tmp_path: Path) -> None:
    path = tmp_path / "authority-keys.json"
    path.write_text(
        json.dumps(
            {"acceptance-r11": base64.b64encode(b"z" * 32).decode("ascii")}
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="AUTHORITY_PUBLIC_KEY_CONFLICT"):
        _config(path).effective_authority_public_keys()


def test_missing_external_public_trust_store_preserves_embedded_acceptance_key(
    tmp_path: Path,
) -> None:
    keys = _config(tmp_path / "missing.json").effective_authority_public_keys()

    assert list(keys) == ["acceptance-r11"]


def test_external_public_trust_store_can_be_the_sole_runtime_root(tmp_path: Path) -> None:
    path = tmp_path / "authority-keys.json"
    durable = base64.b64encode(b"d" * 32).decode("ascii")
    path.write_text(
        json.dumps({"workspace-c7r-v1": durable}),
        encoding="utf-8",
    )
    config = _config(path).model_copy(update={"authority_public_keys_b64": {}})

    keys = config.effective_authority_public_keys()

    assert keys == {"workspace-c7r-v1": durable}


def test_empty_authority_root_fails_closed(tmp_path: Path) -> None:
    config = _config(None).model_copy(update={"authority_public_keys_b64": {}})

    with pytest.raises(RuntimeError, match="AUTHORITY_PUBLIC_KEY_STORE_EMPTY"):
        config.effective_authority_public_keys()


def test_accepts_workspace_cross_repo_signature_vector() -> None:
    envelope = json.loads("{\"contract_version\":\"1.0\",\"task_id\":\"C7R-CROSS-CONTRACT-VECTOR-001\",\"project_id\":\"PALWAKF_AGENTIC_AI_SYSTEM\",\"project_aliases\":[],\"repository_id\":\"firasfanon/palwakf_agenticAi_system\",\"executor_id\":\"Futuer-IT\",\"task_type\":\"C7R_PHASE_A\",\"mutation_class\":\"SERVICE_MUTATION\",\"requested_capability_id\":\"c7r.phase_a\",\"arguments\":{\"operation\":\"preflight\"},\"authority_ref\":\"workspace://c7r/pre-gate-a-vector\",\"execution_lease\":{\"lease_id\":\"lease-C7R-CROSS-CONTRACT-VECTOR-001\",\"task_id\":\"C7R-CROSS-CONTRACT-VECTOR-001\",\"project_id\":\"PALWAKF_AGENTIC_AI_SYSTEM\",\"issuer_ref\":\"workspace://c7r/pre-gate-a-vector\",\"approval_class\":\"PRE_GATE_A_BOOTSTRAP\",\"allowed_capability_ids\":[\"c7r.phase_a\"],\"allowed_mutation_classes\":[\"SERVICE_MUTATION\"],\"scope_paths\":[\"C:\\\\ProgramData\\\\PalWakf\\\\c7r_phase_a_v1\"],\"base_sha\":\"1111111111111111111111111111111111111111\",\"branch\":\"task/AGENTIC-C7R-PRE-GATE-A-PHASE-A-CAPABILITY-V1\",\"issued_at\":\"2026-09-30T17:00:00.7654321+00:00\",\"expires_at\":\"2099-09-30T17:30:00.0000000+00:00\",\"revocation_state\":\"ACTIVE\"},\"expected_remote_head\":\"1111111111111111111111111111111111111111\",\"expected_base_sha\":\"1111111111111111111111111111111111111111\",\"task_branch\":\"task/AGENTIC-C7R-PRE-GATE-A-PHASE-A-CAPABILITY-V1\",\"scope_paths\":[\"C:\\\\ProgramData\\\\PalWakf\\\\c7r_phase_a_v1\"],\"prohibited_actions\":[\"main_merge\",\"baseline_promotion\",\"production_mutation\",\"shared_db_mutation\",\"arbitrary_shell\"],\"idempotency_key\":\"c7r-cross-contract-vector-001\",\"nonce\":\"c7r-cross-contract-vector-nonce-001\",\"issued_at\":\"2026-09-30T17:00:00.1234567+00:00\",\"expires_at\":\"2099-09-30T17:20:00.0000000+00:00\",\"max_duration_seconds\":1800,\"evidence_requirements\":[\"authority\",\"runtime_admission\",\"zero_manual_terminal\",\"no_normal_api_key_fallback\"],\"transport_metadata\":{},\"correlation_id\":\"c7r-cross-contract-vector-001\",\"checkpoint_id\":null,\"depends_on_task_ids\":[],\"model_provider_metadata\":{}}")
    envelope["authority_proof"] = {
        "algorithm": "ED25519",
        "key_id": "workspace-c7r-vector-v1",
        "signature_b64": (
            "52Hhw/BM5qUB1cpZ+x5J2uEqT5ysbvXNihcOJJdw8H5AbSdJdns7Zy/FvxhQ75+G"
            "705ezzwAHhAYAKFH44fuBA=="
        ),
    }
    model = TaskEnvelopeV1.model_validate(envelope)
    verifier = Ed25519AuthorityVerifierV1(
        {
            "workspace-c7r-vector-v1":
                "iojj3XQJ8ZX9UtstPLpdcspnCb8dlBIb83SIAbQPb1w="
        }
    )

    accepted, blockers = verifier.verify(
        model,
        now=datetime(2026, 9, 30, 17, 5, tzinfo=UTC),
    )

    assert accepted is True
    assert blockers == ()
    assert model.envelope_hash() == (
        "4ffb363168c1edef371d0fee4660ab19bd30e147d51175fbe382bde1699277e9"
    )
