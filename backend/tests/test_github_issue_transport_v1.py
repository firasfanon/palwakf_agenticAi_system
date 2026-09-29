from __future__ import annotations

import json

import pytest

from palwakf_local_agents.github_issue_transport_v1 import (
    BEGIN,
    END,
    GitHubIssueTransportSettingsV1,
    GitHubIssueTransportV1,
    TransportError,
)


def test_extract_envelope_requires_markers_and_object():
    body = BEGIN + "\n{\"task_id\":\"t1\",\"executor_id\":\"e1\"}\n" + END
    parsed = GitHubIssueTransportV1._extract_envelope(body)
    assert parsed["task_id"] == "t1"
    with pytest.raises(TransportError):
        GitHubIssueTransportV1._extract_envelope("{}")


def test_ack_rejected_task_posts_ack_and_closes_issue():
    transport = GitHubIssueTransportV1(
        GitHubIssueTransportSettingsV1(
            repository="owner/repo",
            token_env_var=None,
            token_protected_path="C:\\ProgramData\\PalWakf\\secret.dpapi",
        )
    )
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"labels": [{"name": "question"}, {"name": "keep-me"}]}
        return {}

    transport._request = fake_request  # type: ignore[method-assign]
    transport.ack_task({"issue_number": 77}, status="REJECTED")

    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/issues/77/comments")
    assert "PALWAKF_ACK_V1" in calls[0][2]["body"]
    assert calls[1][0] == "GET"
    assert calls[2] == (
        "PATCH",
        "/repos/owner/repo/issues/77",
        {"state": "closed", "state_reason": "not_planned", "labels": ["keep-me"]},
    )


def test_ack_completed_task_closes_issue_as_completed():
    transport = GitHubIssueTransportV1(
        GitHubIssueTransportSettingsV1(
            repository="owner/repo",
            token_env_var=None,
            token_protected_path="C:\\ProgramData\\PalWakf\\secret.dpapi",
        )
    )
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"labels": [{"name": "question"}]}
        return {}

    transport._request = fake_request  # type: ignore[method-assign]
    transport.ack_task({"issue_number": 78}, status="COMPLETED")

    assert calls[-1] == (
        "PATCH",
        "/repos/owner/repo/issues/78",
        {"state": "closed", "state_reason": "completed", "labels": []},
    )


def _task_issue(number: int = 91, *, state: str = "open"):
    body = BEGIN + "\n" + '{"task_id":"t1","executor_id":"DESKTOP-S5A0JSB"}' + "\n" + END
    return {
        "number": number,
        "id": number + 1000,
        "state": state,
        "body": body,
        "labels": [{"name": "question"}],
    }


def test_claim_rechecks_live_issue_state_before_posting_claim():
    transport = GitHubIssueTransportV1(
        GitHubIssueTransportSettingsV1(
            repository="owner/repo",
            task_label="question",
            token_env_var=None,
            token_protected_path="C:\\ProgramData\\PalWakf\\secret.dpapi",
        )
    )
    calls = []
    listed = _task_issue()
    closed = _task_issue(state="closed")

    def fake_request(method, path, body=None):
        calls.append((method, path, body))
        if "?state=open&labels=" in path:
            return [listed]
        if method == "GET" and path.endswith("/issues/91"):
            return closed
        raise AssertionError((method, path, body))

    transport._request = fake_request  # type: ignore[method-assign]
    assert transport.claim_task(executor_id="DESKTOP-S5A0JSB") is None
    assert not any(method == "POST" for method, _, _ in calls)


def test_claim_skips_issue_with_terminal_ack_even_if_open_list_is_stale():
    transport = GitHubIssueTransportV1(
        GitHubIssueTransportSettingsV1(
            repository="owner/repo",
            task_label="question",
            token_env_var=None,
            token_protected_path="C:\\ProgramData\\PalWakf\\secret.dpapi",
        )
    )
    calls = []
    issue = _task_issue()

    def fake_request(method, path, body=None):
        calls.append((method, path, body))
        if "?state=open&labels=" in path:
            return [issue]
        if method == "GET" and path.endswith("/issues/91"):
            return issue
        if method == "GET" and "/issues/91/comments?" in path:
            return [{
                "body": "PALWAKF_ACK_V1\n```json\n"
                + json.dumps({"status": "COMPLETED"})
                + "\n```"
            }]
        raise AssertionError((method, path, body))

    transport._request = fake_request  # type: ignore[method-assign]
    assert transport.claim_task(executor_id="DESKTOP-S5A0JSB") is None
    assert not any(method == "POST" for method, _, _ in calls)
