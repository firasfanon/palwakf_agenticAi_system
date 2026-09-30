from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from palwakf_local_agents import c7r_phase_a_v1 as c7r
from palwakf_local_agents.outbound_capabilities_v1 import (
    CapabilityError,
    default_capability_registry_v1,
)


def test_authorization_url_matches_openai_oss_pkce_contract() -> None:
    url = c7r._authorization_url(
        client_id="dynamic_agent_client",
        redirect_uri="http://127.0.0.1:48123/auth/callback",
        host_id="urn:uuid:11111111-1111-4111-8111-111111111111",
        state="state-value",
        nonce="nonce-value",
        challenge="challenge-value",
    )
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://auth.openai.com/api/accounts/authorize"
    )
    assert query["client_id"] == ["dynamic_agent_client"]
    assert query["redirect_uri"] == ["http://127.0.0.1:48123/auth/callback"]
    assert query["resource"] == ["https://api.openai.com/v1"]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["ext_agent_host_id"][0].startswith("urn:uuid:")
    assert "chatgpt.tokens.use.direct" in query["scope"][0].split()


def test_reauthorization_omits_initial_agent_name_hint() -> None:
    url = c7r._authorization_url(
        client_id="oaiapp_existing_client",
        redirect_uri="http://127.0.0.1:48124/auth/callback",
        host_id="urn:uuid:11111111-1111-4111-8111-111111111111",
        state="state-value",
        nonce="nonce-value",
        challenge="challenge-value",
    )
    query = parse_qs(urlsplit(url).query)

    assert query["client_id"] == ["oaiapp_existing_client"]
    assert "agent_name_hint" not in query


def test_app_server_command_uses_chatgpt_plan_responses_provider() -> None:
    command = c7r._app_server_command(Path("codex.exe"))
    joined = "\n".join(command)

    assert command[:4] == ["codex.exe", "app-server", "--listen", "stdio://"]
    assert 'model_provider="openai_chatgpt_plan"' in command
    assert 'model_providers.openai_chatgpt_plan.env_key="ACCESS_TOKEN"' in command
    assert 'model_providers.openai_chatgpt_plan.wire_api="responses"' in command
    assert "model_providers.openai_chatgpt_plan.requires_openai_auth=false" in command
    assert "model_providers.openai_chatgpt_plan.supports_websockets=false" in command
    assert "OPENAI_API_KEY" not in joined
    assert "CODEX_API_KEY" not in joined


def test_registry_admits_only_named_c7r_service_mutation() -> None:
    descriptor = default_capability_registry_v1().resolve("c7r.phase_a")

    assert descriptor.capability_id == "c7r.phase_a"
    assert descriptor.mutation_class == "SERVICE_MUTATION"
    assert descriptor.idempotency_class == "STATEFUL_GOVERNED"


def test_preflight_returns_redacted_safe_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "c7r"
    monkeypatch.setattr(c7r, "_state_root", lambda: state_root)
    monkeypatch.setattr(
        c7r,
        "_runtime_admission",
        lambda _ctx: {
            "agentic_source_head": "1" * 40,
            "agentic_source_branch": "task/AGENTIC-C7R-PRE-GATE-A-PHASE-A-CAPABILITY-V1",
            "capability_id": "c7r.phase_a",
            "admitted_at": "2026-09-30T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        c7r,
        "_codex_preflight",
        lambda: {
            "codex_version": "0.159.1",
            "binary_sha256_matches_pinned_asset": True,
            "normal_openai_api_key_required": False,
            "normal_codex_api_key_required": False,
        },
    )
    monkeypatch.setattr(
        c7r,
        "_credential_status",
        lambda: {
            "credential_present": False,
            "registration_present": False,
            "tokens_exposed": False,
        },
    )
    ctx = SimpleNamespace(
        scope_paths=(str(state_root),),
        allowed_roots=(str(tmp_path),),
    )

    result = c7r.c7r_phase_a(ctx, {"operation": "preflight"})
    summary = json.loads(str(result["_evidence_summary"]))

    assert summary["operation"] == "preflight"
    assert summary["codex_version"] == "0.159.1"
    assert summary["credential_present"] is False
    assert summary["tokens_exposed"] is False
    assert "access_token" not in result["_evidence_summary"]
    assert "refresh_token" not in result["_evidence_summary"]
    assert "id_token" not in result["_evidence_summary"]


def test_c7r_handler_fails_closed_outside_admitted_operation(tmp_path: Path) -> None:
    descriptor = default_capability_registry_v1().resolve("c7r.phase_a")
    ctx = SimpleNamespace(
        scope_paths=(str(tmp_path),),
        allowed_roots=(str(tmp_path),),
        executor_id="DESKTOP-S5A0JSB",
        repository_id="firasfanon/palwakf_agenticAi_system",
        task_branch="task/AGENTIC-C7R-PRE-GATE-A-PHASE-A-CAPABILITY-V1",
        expected_base_sha="1" * 40,
        max_output_bytes=131072,
    )

    with pytest.raises(CapabilityError, match="C7R_OPERATION_NOT_ADMITTED"):
        descriptor.handler(ctx, {"operation": "arbitrary_shell"})


def test_evidence_summary_has_no_oauth_url_or_token_fields() -> None:
    result = c7r._with_evidence_summary(
        {
            "operation": "oauth_prepare",
            "state": "OAUTH_PENDING",
            "browser_launch_attempted": True,
            "browser_launch_reported_success": False,
            "authorization_url_local_file": r"C:\ProgramData\PalWakf\c7r_phase_a_v1\authorization-url.txt",
            "tokens_exposed": False,
        }
    )
    summary = str(result["_evidence_summary"]).casefold()

    assert "authorization-url" not in summary
    assert "access_token" not in summary
    assert "refresh_token" not in summary
    assert "id_token" not in summary
