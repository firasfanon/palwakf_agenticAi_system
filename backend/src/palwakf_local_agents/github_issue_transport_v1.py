from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field

from palwakf_local_agents.windows_protected_secret_v1 import read_windows_protected_text


BEGIN = "PALWAKF_TASK_ENVELOPE_V1_BEGIN"
END = "PALWAKF_TASK_ENVELOPE_V1_END"


class TransportError(RuntimeError):
    pass


class TaskTransport(Protocol):
    def health(self) -> Mapping[str, Any]: ...
    def claim_task(self, *, executor_id: str) -> Mapping[str, Any] | None: ...
    def read_envelope(self, claimed: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def ack_task(self, claimed: Mapping[str, Any], *, status: str) -> None: ...
    def publish_progress(self, claimed: Mapping[str, Any], payload: Mapping[str, Any]) -> None: ...
    def publish_result(self, claimed: Mapping[str, Any], payload: Mapping[str, Any]) -> None: ...
    def publish_heartbeat(self, payload: Mapping[str, Any]) -> None: ...
    def release_or_fail(self, claimed: Mapping[str, Any], *, reason: str) -> None: ...


class GitHubIssueTransportSettingsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    task_label: str = "palwakf-local-executor"
    token_env_var: str | None = "PALWAKF_GITHUB_TOKEN"
    token_protected_path: str | None = None
    api_base: str = "https://api.github.com"
    heartbeat_comment_id: int | None = None
    user_agent: str = "palwakf-outbound-local-executor-v1"


class GitHubIssueTransportV1:
    transport_id = "github-issues-v1"

    def __init__(self, settings: GitHubIssueTransportSettingsV1):
        self.settings = settings

    def _token(self) -> str:
        if self.settings.token_env_var:
            token = os.environ.get(self.settings.token_env_var, "")
            if token:
                return token
        if self.settings.token_protected_path:
            return read_windows_protected_text(self.settings.token_protected_path)
        raise TransportError("GITHUB_TOKEN_NOT_SET")

    def _request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Any:
        url = self.settings.api_base.rstrip("/") + path
        data = None if body is None else json.dumps(dict(body)).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": self.settings.user_agent,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
                return json.loads(payload.decode("utf-8")) if payload else None
        except Exception as exc:
            raise TransportError(f"GITHUB_HTTP_FAILURE:{type(exc).__name__}") from exc

    @staticmethod
    def _extract_envelope(body: str) -> Mapping[str, Any]:
        start = body.find(BEGIN)
        end = body.find(END)
        if start < 0 or end < 0 or end <= start:
            raise TransportError("TASK_ENVELOPE_MARKERS_MISSING")
        payload = body[start + len(BEGIN):end].strip()
        try:
            value = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise TransportError("TASK_ENVELOPE_JSON_INVALID") from exc
        if not isinstance(value, dict):
            raise TransportError("TASK_ENVELOPE_MUST_BE_OBJECT")
        return value

    def health(self) -> Mapping[str, Any]:
        owner, repo = self.settings.repository.split("/", 1)
        self._request("GET", f"/repos/{owner}/{repo}")
        return {"transport_id": self.transport_id, "status": "HEALTHY"}

    def claim_task(self, *, executor_id: str) -> Mapping[str, Any] | None:
        owner, repo = self.settings.repository.split("/", 1)
        label = urllib.parse.quote(self.settings.task_label)
        issues = self._request(
            "GET",
            f"/repos/{owner}/{repo}/issues?state=open&labels={label}&per_page=20&sort=created&direction=asc",
        )
        for issue in issues or []:
            if "pull_request" in issue:
                continue
            body = issue.get("body") or ""
            try:
                envelope = self._extract_envelope(body)
            except TransportError:
                continue
            if envelope.get("executor_id") != executor_id:
                continue
            claim = {
                "schema": "palwakf.github_issue_claim.v1",
                "executor_id": executor_id,
                "task_id": envelope.get("task_id"),
                "claimed_at": datetime.now(UTC).isoformat(),
            }
            self._request(
                "POST",
                f"/repos/{owner}/{repo}/issues/{issue['number']}/comments",
                {"body": "PALWAKF_CLAIM_V1\n\x60\x60\x60json\n" + json.dumps(claim, sort_keys=True) + "\n\x60\x60\x60"},
            )
            return {"issue_number": issue["number"], "issue_id": issue["id"], "envelope": envelope}
        return None

    def read_envelope(self, claimed: Mapping[str, Any]) -> Mapping[str, Any]:
        envelope = claimed.get("envelope")
        if not isinstance(envelope, dict):
            raise TransportError("CLAIMED_ENVELOPE_MISSING")
        return envelope

    def _comment(self, claimed: Mapping[str, Any], marker: str, payload: Mapping[str, Any]) -> None:
        owner, repo = self.settings.repository.split("/", 1)
        number = int(claimed["issue_number"])
        body = marker + "\n\x60\x60\x60json\n" + json.dumps(
            dict(payload), ensure_ascii=False, sort_keys=True, default=str
        ) + "\n\x60\x60\x60"
        self._request("POST", f"/repos/{owner}/{repo}/issues/{number}/comments", {"body": body})

    def ack_task(self, claimed: Mapping[str, Any], *, status: str) -> None:
        self._comment(claimed, "PALWAKF_ACK_V1", {"status": status, "at": datetime.now(UTC).isoformat()})

    def publish_progress(self, claimed: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
        self._comment(claimed, "PALWAKF_PROGRESS_V1", payload)

    def publish_result(self, claimed: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
        self._comment(claimed, "PALWAKF_RESULT_V1", payload)

    def publish_heartbeat(self, payload: Mapping[str, Any]) -> None:
        comment_id = self.settings.heartbeat_comment_id
        if comment_id is None:
            return
        owner, repo = self.settings.repository.split("/", 1)
        body = "PALWAKF_HEARTBEAT_V1\n\x60\x60\x60json\n" + json.dumps(
            dict(payload), sort_keys=True, default=str
        ) + "\n\x60\x60\x60"
        self._request("PATCH", f"/repos/{owner}/{repo}/issues/comments/{comment_id}", {"body": body})

    def release_or_fail(self, claimed: Mapping[str, Any], *, reason: str) -> None:
        self._comment(claimed, "PALWAKF_RELEASE_OR_FAIL_V1", {"reason": reason, "at": datetime.now(UTC).isoformat()})
