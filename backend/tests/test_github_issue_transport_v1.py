import pytest
from palwakf_local_agents.github_issue_transport_v1 import GitHubIssueTransportV1, TransportError, BEGIN, END


def test_extract_envelope_requires_markers_and_object():
    body = BEGIN + "\n{\"task_id\":\"t1\",\"executor_id\":\"e1\"}\n" + END
    parsed = GitHubIssueTransportV1._extract_envelope(body)
    assert parsed["task_id"] == "t1"
    with pytest.raises(TransportError):
        GitHubIssueTransportV1._extract_envelope("{}")
