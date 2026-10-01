from __future__ import annotations

import pytest

from palwakf_local_agents.outbound_capabilities_v1 import CapabilityContextV1
from palwakf_local_agents.workspace_drive_capabilities_v1 import (
    DriveDocumentV1,
    InMemoryWorkspaceDriveAdapterV1,
    WorkspaceDriveCapabilityError,
    workspace_drive_append,
    workspace_drive_read,
    workspace_drive_search,
    workspace_drive_update,
)


def _ctx(scopes: tuple[str, ...]) -> CapabilityContextV1:
    return CapabilityContextV1(
        executor_id="Futuer-IT",
        repository_id="firasfanon/palwakf_agenticAi_system",
        allowed_roots=(r"C:\repo",),
        scope_paths=scopes,
        task_branch="task/DRIVE-TEST-V1",
        expected_base_sha="1" * 40,
    )


def _adapter() -> InMemoryWorkspaceDriveAdapterV1:
    return InMemoryWorkspaceDriveAdapterV1(
        (
            DriveDocumentV1(
                document_id="doc-1",
                folder_id="folder-1",
                title="Current State",
                body="alpha beta",
                revision="7",
            ),
        )
    )


def test_drive_read_requires_signed_document_scope() -> None:
    adapter = _adapter()

    result = workspace_drive_read(
        adapter,
        _ctx(("drive:doc:doc-1",)),
        {"document_id": "doc-1"},
    )

    assert result["revision"] == "7"
    assert result["body"] == "alpha beta"

    with pytest.raises(
        WorkspaceDriveCapabilityError,
        match="DRIVE_DOCUMENT_OUTSIDE_SIGNED_SCOPE",
    ):
        workspace_drive_read(adapter, _ctx(()), {"document_id": "doc-1"})


def test_drive_search_is_bounded_to_signed_folder_scope() -> None:
    result = workspace_drive_search(
        _adapter(),
        _ctx(("drive:folder:folder-1",)),
        {"query": "alpha"},
    )

    assert [item["document_id"] for item in result["documents"]] == ["doc-1"]


def test_drive_update_fails_closed_on_revision_drift() -> None:
    adapter = _adapter()
    ctx = _ctx(("drive:doc:doc-1",))

    with pytest.raises(
        WorkspaceDriveCapabilityError,
        match="DRIVE_REVISION_DRIFT",
    ):
        workspace_drive_update(
            adapter,
            ctx,
            {
                "document_id": "doc-1",
                "expected_revision": "6",
                "body": "new",
            },
        )

    updated = workspace_drive_update(
        adapter,
        ctx,
        {
            "document_id": "doc-1",
            "expected_revision": "7",
            "body": "new",
        },
    )
    assert updated["before_revision"] == "7"
    assert updated["after_revision"] == "8"


def test_drive_append_requires_current_revision() -> None:
    adapter = _adapter()
    ctx = _ctx(("drive:doc:doc-1",))

    result = workspace_drive_append(
        adapter,
        ctx,
        {
            "document_id": "doc-1",
            "expected_revision": "7",
            "text": " gamma",
        },
    )

    assert result["after_revision"] == "8"
    document = adapter.read_document("doc-1")
    assert document.body == "alpha beta gamma"
