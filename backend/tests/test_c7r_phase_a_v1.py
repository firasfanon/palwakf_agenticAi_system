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


def test_codex_executable_prefers_explicit_provider_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    codex = tmp_path / "codex.exe"
    codex.write_bytes(b"provider")
    monkeypatch.setenv("PALWAKF_CODEX_EXECUTABLE", str(codex))
    monkeypatch.setattr(c7r.shutil, "which", lambda _name: None)

    assert c7r._codex_executable() == codex.resolve()


def test_codex_executable_invalid_explicit_provider_path_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "PALWAKF_CODEX_EXECUTABLE",
        str(tmp_path / "missing-codex.exe"),
    )

    with pytest.raises(c7r.C7RPhaseAError, match="CODEX_EXPLICIT_PATH_INVALID"):
        c7r._codex_executable()


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
            "agentic_source_branch": "task/AGENTIC-C7R-EXECUTOR-ID-FUTUER-IT-V1",
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
        executor_id="Futuer-IT",
        repository_id="firasfanon/palwakf_agenticAi_system",
        task_branch="task/AGENTIC-C7R-EXECUTOR-ID-FUTUER-IT-V1",
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


def test_oauth_prepare_starts_in_process_callback_listener(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_root = tmp_path / "c7r"
    monkeypatch.setattr(c7r, "_state_root", lambda: state_root)
    monkeypatch.setattr(
        c7r,
        "_stable_host_id",
        lambda: "urn:uuid:11111111-1111-4111-8111-111111111111",
    )
    monkeypatch.setattr(c7r, "_protected_read_json", lambda _path: None)
    monkeypatch.setattr(c7r, "_protected_write_json", lambda _path, _value: None)
    monkeypatch.setattr(c7r, "_reserve_loopback_port", lambda: 48125)
    seen: dict[str, int] = {}

    def start_listener(port: int) -> object:
        seen["port"] = port
        return object()

    monkeypatch.setattr(c7r, "_start_callback_listener", start_listener)

    def open_browser(*_args, **_kwargs) -> bool:
        pending_status = json.loads(
            (state_root / "status.json").read_text(encoding="utf-8")
        )
        assert pending_status["state"] == "OAUTH_PENDING"
        c7r._safe_write_json(
            state_root / "status.json",
            {
                "state": "OAUTH_AUTHENTICATED",
                "tokens_exposed": False,
            },
        )
        return True

    monkeypatch.setattr(c7r.webbrowser, "open", open_browser)

    result = c7r._oauth_prepare()
    final_status = json.loads(
        (state_root / "status.json").read_text(encoding="utf-8")
    )

    assert seen == {"port": 48125}
    assert result["state"] == "OAUTH_PENDING"
    assert result["callback_port"] == 48125
    assert result["browser_launch_reported_success"] is True
    assert final_status["state"] == "OAUTH_AUTHENTICATED"


def test_callback_listener_reports_ready_in_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, int] = {}

    def fake_server(port: int, *, ready=None) -> None:
        seen["port"] = port
        assert ready is not None
        ready.set()

    monkeypatch.setattr(c7r, "_run_callback_server", fake_server)

    thread = c7r._start_callback_listener(48126)
    thread.join(timeout=1)

    assert seen == {"port": 48126}
    assert not thread.is_alive()


def test_callback_listener_start_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_server(_port: int, *, ready=None) -> None:
        raise OSError("bind failed")

    monkeypatch.setattr(c7r, "_run_callback_server", fail_server)

    with pytest.raises(
        c7r.C7RPhaseAError,
        match="OAUTH_CALLBACK_LISTENER_START_FAILED:OSError",
    ):
        c7r._start_callback_listener(48127)


def test_callback_listener_binds_loopback_before_return() -> None:
    port = c7r._reserve_loopback_port()
    thread = c7r._start_callback_listener(port)

    with c7r.socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
        sock.sendall(
            b"GET /not-auth-callback HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Connection: close\r\n\r\n"
        )
        response = sock.recv(1024)

    thread.join(timeout=2)

    assert b"404" in response
    assert not thread.is_alive()


def test_safe_turn_error_classification_uses_closed_string_variant() -> None:
    kind, status = c7r._safe_turn_error_classification(
        {
            "error": {
                "message": "must never be emitted",
                "codexErrorInfo": "unauthorized",
            }
        }
    )

    assert kind == "unauthorized"
    assert status is None


def test_safe_turn_error_classification_reads_only_structured_http_status() -> None:
    kind, status = c7r._safe_turn_error_classification(
        {
            "error": {
                "message": "must never be emitted",
                "additionalDetails": "must never be emitted",
                "codexErrorInfo": {
                    "responseStreamConnectionFailed": {
                        "httpStatusCode": 403,
                    }
                },
            }
        }
    )

    assert kind == "responseStreamConnectionFailed"
    assert status == 403


def test_safe_turn_error_classification_fails_closed_without_codex_info() -> None:
    kind, status = c7r._safe_turn_error_classification(
        {
            "error": {
                "message": "provider-specific secret-looking text",
                "additionalDetails": "not part of the classifier",
            }
        }
    )

    assert kind == "unclassified"
    assert status is None


def test_model_catalog_returns_only_safe_visible_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        c7r,
        "_credentials_with_refresh",
        lambda: {"access_token": "secret-access-token"},
    )

    def catalog(access_token: str) -> list[dict[str, str]]:
        assert access_token == "secret-access-token"
        return [
            {"slug": "model-a", "display_name": "Model A"},
            {"slug": "model-b", "display_name": "Model B"},
        ]

    monkeypatch.setattr(c7r, "_account_model_catalog", catalog)

    result = c7r._model_catalog()

    assert result["state"] == "COMPLETED"
    assert result["visible_model_count"] == 2
    assert result["models"][0]["slug"] == "model-a"
    assert result["tokens_exposed"] is False
    assert "access_token" not in result


def test_model_catalog_evidence_summary_contains_no_credentials() -> None:
    result = c7r._with_evidence_summary(
        {
            "operation": "model_catalog",
            "state": "COMPLETED",
            "visible_model_count": 1,
            "models": [{"slug": "model-a", "display_name": "Model A"}],
            "tokens_exposed": False,
        }
    )
    summary = json.loads(str(result["_evidence_summary"]))

    assert summary["operation"] == "model_catalog"
    assert summary["visible_model_count"] == 1
    assert summary["models"] == [
        {"slug": "model-a", "display_name": "Model A"}
    ]
    assert "access_token" not in summary
    assert summary["tokens_exposed"] is False


def test_c7r_handler_admits_model_catalog(
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
            "agentic_source_branch": "task/test",
            "capability_id": "c7r.phase_a",
        },
    )
    monkeypatch.setattr(
        c7r,
        "_model_catalog",
        lambda: {
            "operation": "model_catalog",
            "state": "COMPLETED",
            "visible_model_count": 1,
            "models": [{"slug": "model-a", "display_name": "Model A"}],
            "tokens_exposed": False,
        },
    )
    ctx = SimpleNamespace(
        scope_paths=(str(state_root),),
        allowed_roots=(str(tmp_path),),
    )

    result = c7r.c7r_phase_a(ctx, {"operation": "model_catalog"})
    summary = json.loads(str(result["_evidence_summary"]))

    assert summary["state"] == "COMPLETED"
    assert summary["models"][0]["slug"] == "model-a"


def test_safe_direct_error_shape_redacts_raw_text() -> None:
    raw = json.dumps(
        {
            "detail": "sensitive admission text",
            "error": {
                "message": "provider secret-looking message",
                "code": "subscription_sharing_user_not_eligible",
                "param": "model",
            },
        }
    ).encode("utf-8")

    result = c7r._safe_direct_error_shape(raw)
    serialized = json.dumps(result)

    assert result["body_kind"] == "object"
    assert result["top_level_keys"] == ["detail", "error"]
    assert result["error_keys"] == ["code", "message", "param"]
    assert result["error_code"] == "subscription_sharing_user_not_eligible"
    assert result["error_param"] == "model"
    assert result["detail_present"] is True
    assert "sensitive admission text" not in serialized
    assert "provider secret-looking message" not in serialized


def test_direct_admission_probe_captures_safe_http_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        c7r,
        "_credentials_with_refresh",
        lambda: {"access_token": "secret-access-token"},
    )
    monkeypatch.setattr(
        c7r,
        "_model_for_account",
        lambda token, requested: (
            "gpt-5.6-sol"
            if token == "secret-access-token" and requested == "gpt-5.6-sol"
            else (_ for _ in ()).throw(AssertionError("unexpected model lookup"))
        ),
    )
    captured: dict[str, object] = {}

    def fail_with_403(request, timeout=0):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        assert timeout == 90
        raise c7r.urllib.error.HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {"x-request-id": "req_safe_123"},
            __import__("io").BytesIO(
                json.dumps(
                    {
                        "error": {
                            "message": "must not escape",
                            "code": "subscription_sharing_user_not_eligible",
                            "param": "model",
                        }
                    }
                ).encode("utf-8")
            ),
        )

    monkeypatch.setattr(c7r.urllib.request, "urlopen", fail_with_403)

    result = c7r._direct_admission_probe("gpt-5.6-sol")
    serialized = json.dumps(result)
    body = captured["body"]

    assert body == {
        "model": "gpt-5.6-sol",
        "input": [
            {
                "role": "user",
                "content": "Say exactly: PALWAKF_C7R_DIRECT_PROBE_OK",
            }
        ],
        "store": False,
        "stream": True,
    }
    assert result["state"] == "ADMISSION_BLOCKED"
    assert result["http_status"] == 403
    assert result["request_id"] == "req_safe_123"
    assert result["error_code"] == "subscription_sharing_user_not_eligible"
    assert result["error_param"] == "model"
    assert "must not escape" not in serialized
    assert "secret-access-token" not in serialized


def test_direct_admission_probe_evidence_summary_is_redacted() -> None:
    result = c7r._with_evidence_summary(
        {
            "operation": "direct_admission_probe",
            "state": "ADMISSION_BLOCKED",
            "model": "gpt-5.6-sol",
            "http_status": 403,
            "request_id": "req_safe_123",
            "body_kind": "object",
            "top_level_keys": ["error"],
            "error_keys": ["code", "message"],
            "error_code": "subscription_sharing_user_not_eligible",
            "error_param": None,
            "detail_present": False,
            "terminal_event": None,
            "store": False,
            "stream": True,
            "tokens_exposed": False,
            "normal_openai_api_key_used": False,
            "normal_codex_api_key_used": False,
        }
    )
    summary = json.loads(str(result["_evidence_summary"]))

    assert summary["operation"] == "direct_admission_probe"
    assert summary["http_status"] == 403
    assert summary["request_id"] == "req_safe_123"
    assert summary["error_code"] == "subscription_sharing_user_not_eligible"
    assert summary["tokens_exposed"] is False
