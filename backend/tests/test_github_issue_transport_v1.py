from __future__ import annotations

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
        return {}

    transport._request = fake_request  # type: ignore[method-assign]
    transport.ack_task({"issue_number": 77}, status="REJECTED")

    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/issues/77/comments")
    assert "PALWAKF_ACK_V1" in calls[0][2]["body"]
    assert calls[1] == (
        "PATCH",
        "/repos/owner/repo/issues/77",
        {"state": "closed", "state_reason": "not_planned"},
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
        return {}

    transport._request = fake_request  # type: ignore[method-assign]
    transport.ack_task({"issue_number": 78}, status="COMPLETED")

    assert calls[-1] == (
        "PATCH",
        "/repos/owner/repo/issues/78",
        {"state": "closed", "state_reason": "completed"},
    )
