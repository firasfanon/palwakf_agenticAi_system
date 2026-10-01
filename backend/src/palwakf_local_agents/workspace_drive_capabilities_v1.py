from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class WorkspaceDriveCapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class DriveDocumentV1:
    document_id: str
    folder_id: str | None
    title: str
    body: str
    revision: str


class WorkspaceDriveAdapter(Protocol):
    adapter_id: str

    def health(self) -> Mapping[str, Any]: ...
    def search(self, query: str, *, folder_ids: tuple[str, ...], limit: int) -> tuple[DriveDocumentV1, ...]: ...
    def list_folder(self, folder_id: str, *, limit: int) -> tuple[DriveDocumentV1, ...]: ...
    def read_document(self, document_id: str) -> DriveDocumentV1: ...
    def create_document(self, *, folder_id: str, title: str, body: str) -> DriveDocumentV1: ...
    def update_document(self, *, document_id: str, expected_revision: str, body: str) -> DriveDocumentV1: ...
    def append_document(self, *, document_id: str, expected_revision: str, text: str) -> DriveDocumentV1: ...


class UnavailableWorkspaceDriveAdapterV1:
    adapter_id = "workspace-drive-unavailable-v1"

    def health(self) -> Mapping[str, Any]:
        return {"adapter_id": self.adapter_id, "state": "NOT_CONFIGURED", "writes_enabled": False}

    @staticmethod
    def _unavailable() -> None:
        raise WorkspaceDriveCapabilityError("WORKSPACE_DRIVE_LIVE_ADAPTER_NOT_CONFIGURED")

    def search(self, query: str, *, folder_ids: tuple[str, ...], limit: int):
        self._unavailable()

    def list_folder(self, folder_id: str, *, limit: int):
        self._unavailable()

    def read_document(self, document_id: str):
        self._unavailable()

    def create_document(self, *, folder_id: str, title: str, body: str):
        self._unavailable()

    def update_document(self, *, document_id: str, expected_revision: str, body: str):
        self._unavailable()

    def append_document(self, *, document_id: str, expected_revision: str, text: str):
        self._unavailable()


class InMemoryWorkspaceDriveAdapterV1:
    adapter_id = "workspace-drive-memory-v1"

    def __init__(self, documents: tuple[DriveDocumentV1, ...] = ()) -> None:
        self._documents = {item.document_id: item for item in documents}
        self._next_id = 1

    def health(self) -> Mapping[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "state": "READY",
            "writes_enabled": True,
            "document_count": len(self._documents),
        }

    def search(self, query: str, *, folder_ids: tuple[str, ...], limit: int) -> tuple[DriveDocumentV1, ...]:
        needle = query.casefold()
        output = [
            item for item in self._documents.values()
            if (not folder_ids or item.folder_id in folder_ids)
            and (needle in item.title.casefold() or needle in item.body.casefold())
        ]
        return tuple(sorted(output, key=lambda item: item.document_id)[:limit])

    def list_folder(self, folder_id: str, *, limit: int) -> tuple[DriveDocumentV1, ...]:
        output = [item for item in self._documents.values() if item.folder_id == folder_id]
        return tuple(sorted(output, key=lambda item: item.document_id)[:limit])

    def read_document(self, document_id: str) -> DriveDocumentV1:
        item = self._documents.get(document_id)
        if item is None:
            raise WorkspaceDriveCapabilityError("DRIVE_DOCUMENT_NOT_FOUND")
        return item

    def create_document(self, *, folder_id: str, title: str, body: str) -> DriveDocumentV1:
        while f"memory-doc-{self._next_id}" in self._documents:
            self._next_id += 1
        document_id = f"memory-doc-{self._next_id}"
        self._next_id += 1
        item = DriveDocumentV1(
            document_id=document_id,
            folder_id=folder_id,
            title=title,
            body=body,
            revision="1",
        )
        self._documents[document_id] = item
        return item

    def update_document(self, *, document_id: str, expected_revision: str, body: str) -> DriveDocumentV1:
        current = self.read_document(document_id)
        if current.revision != expected_revision:
            raise WorkspaceDriveCapabilityError("DRIVE_REVISION_DRIFT")
        item = DriveDocumentV1(
            document_id=current.document_id,
            folder_id=current.folder_id,
            title=current.title,
            body=body,
            revision=str(int(current.revision) + 1),
        )
        self._documents[document_id] = item
        return item

    def append_document(self, *, document_id: str, expected_revision: str, text: str) -> DriveDocumentV1:
        current = self.read_document(document_id)
        return self.update_document(
            document_id=document_id,
            expected_revision=expected_revision,
            body=current.body + text,
        )


class DriveCapabilityContext(Protocol):
    scope_paths: tuple[str, ...]


def _document_scopes(ctx: DriveCapabilityContext) -> set[str]:
    return {
        item.removeprefix("drive:doc:")
        for item in ctx.scope_paths
        if item.startswith("drive:doc:") and len(item) > len("drive:doc:")
    }


def _folder_scopes(ctx: DriveCapabilityContext) -> set[str]:
    return {
        item.removeprefix("drive:folder:")
        for item in ctx.scope_paths
        if item.startswith("drive:folder:") and len(item) > len("drive:folder:")
    }


def _require_doc_scope(ctx: DriveCapabilityContext, document_id: str) -> None:
    if document_id not in _document_scopes(ctx):
        raise WorkspaceDriveCapabilityError("DRIVE_DOCUMENT_OUTSIDE_SIGNED_SCOPE")


def _require_folder_scope(ctx: DriveCapabilityContext, folder_id: str) -> None:
    if folder_id not in _folder_scopes(ctx):
        raise WorkspaceDriveCapabilityError("DRIVE_FOLDER_OUTSIDE_SIGNED_SCOPE")


def _safe_limit(args: Mapping[str, Any]) -> int:
    limit = int(args.get("limit", 20))
    if limit < 1 or limit > 100:
        raise WorkspaceDriveCapabilityError("DRIVE_LIMIT_INVALID")
    return limit


def _safe_text(value: object, *, name: str, max_chars: int) -> str:
    if not isinstance(value, str):
        raise WorkspaceDriveCapabilityError(f"{name}_MUST_BE_STRING")
    if len(value) > max_chars:
        raise WorkspaceDriveCapabilityError(f"{name}_TOO_LARGE")
    return value


def _safe_document(item: DriveDocumentV1, *, include_body: bool) -> dict[str, Any]:
    value = {
        "document_id": item.document_id,
        "folder_id": item.folder_id,
        "title": item.title,
        "revision": item.revision,
    }
    if include_body:
        value["body"] = item.body
    return value


def workspace_drive_health(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    if args:
        raise WorkspaceDriveCapabilityError("DRIVE_HEALTH_TAKES_NO_ARGUMENTS")
    return dict(adapter.health())


def workspace_drive_search(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    query = _safe_text(args.get("query", ""), name="DRIVE_QUERY", max_chars=500)
    folders = tuple(sorted(_folder_scopes(ctx)))
    if not folders:
        raise WorkspaceDriveCapabilityError("DRIVE_FOLDER_SCOPE_REQUIRED")
    items = adapter.search(query, folder_ids=folders, limit=_safe_limit(args))
    return {"query": query, "folder_ids": folders, "documents": [_safe_document(item, include_body=False) for item in items]}


def workspace_drive_list(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    folder_id = str(args.get("folder_id", ""))
    _require_folder_scope(ctx, folder_id)
    items = adapter.list_folder(folder_id, limit=_safe_limit(args))
    return {"folder_id": folder_id, "documents": [_safe_document(item, include_body=False) for item in items]}


def workspace_drive_read(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    document_id = str(args.get("document_id", ""))
    _require_doc_scope(ctx, document_id)
    return _safe_document(adapter.read_document(document_id), include_body=True)


def workspace_drive_find(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    document_id = str(args.get("document_id", ""))
    _require_doc_scope(ctx, document_id)
    pattern = _safe_text(args.get("pattern", ""), name="DRIVE_FIND_PATTERN", max_chars=1000)
    if not pattern:
        raise WorkspaceDriveCapabilityError("DRIVE_FIND_PATTERN_REQUIRED")
    document = adapter.read_document(document_id)
    positions: list[int] = []
    start = 0
    while len(positions) < 100:
        found = document.body.find(pattern, start)
        if found < 0:
            break
        positions.append(found)
        start = found + max(1, len(pattern))
    return {
        "document_id": document_id,
        "revision": document.revision,
        "pattern": pattern,
        "positions": positions,
    }


def workspace_drive_append(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    document_id = str(args.get("document_id", ""))
    _require_doc_scope(ctx, document_id)
    expected_revision = str(args.get("expected_revision", ""))
    if not expected_revision:
        raise WorkspaceDriveCapabilityError("DRIVE_EXPECTED_REVISION_REQUIRED")
    text = _safe_text(args.get("text", ""), name="DRIVE_APPEND_TEXT", max_chars=100000)
    before = adapter.read_document(document_id)
    if before.revision != expected_revision:
        raise WorkspaceDriveCapabilityError("DRIVE_REVISION_DRIFT")
    after = adapter.append_document(
        document_id=document_id,
        expected_revision=expected_revision,
        text=text,
    )
    return {"document_id": document_id, "before_revision": before.revision, "after_revision": after.revision}


def workspace_drive_update(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    document_id = str(args.get("document_id", ""))
    _require_doc_scope(ctx, document_id)
    expected_revision = str(args.get("expected_revision", ""))
    if not expected_revision:
        raise WorkspaceDriveCapabilityError("DRIVE_EXPECTED_REVISION_REQUIRED")
    body = _safe_text(args.get("body", ""), name="DRIVE_DOCUMENT_BODY", max_chars=500000)
    before = adapter.read_document(document_id)
    if before.revision != expected_revision:
        raise WorkspaceDriveCapabilityError("DRIVE_REVISION_DRIFT")
    after = adapter.update_document(
        document_id=document_id,
        expected_revision=expected_revision,
        body=body,
    )
    return {"document_id": document_id, "before_revision": before.revision, "after_revision": after.revision}


def workspace_drive_create(adapter: WorkspaceDriveAdapter, ctx: DriveCapabilityContext, args: Mapping[str, Any]) -> Mapping[str, Any]:
    folder_id = str(args.get("folder_id", ""))
    _require_folder_scope(ctx, folder_id)
    title = _safe_text(args.get("title", ""), name="DRIVE_TITLE", max_chars=300)
    body = _safe_text(args.get("body", ""), name="DRIVE_DOCUMENT_BODY", max_chars=500000)
    if not title.strip():
        raise WorkspaceDriveCapabilityError("DRIVE_TITLE_REQUIRED")
    item = adapter.create_document(folder_id=folder_id, title=title, body=body)
    return _safe_document(item, include_body=False)


def extra_workspace_drive_capabilities_v1(adapter: WorkspaceDriveAdapter | None = None):
    from palwakf_local_agents.outbound_capabilities_v1 import CapabilityDescriptorV1, CapabilityError

    bound = adapter or UnavailableWorkspaceDriveAdapterV1()

    def adapt(handler):
        def wrapped(ctx, args):
            try:
                return handler(bound, ctx, args)
            except WorkspaceDriveCapabilityError as exc:
                raise CapabilityError(str(exc)) from exc
        return wrapped

    read_only = (
        ("workspace_drive.search", workspace_drive_search),
        ("workspace_drive.list", workspace_drive_list),
        ("workspace_drive.read", workspace_drive_read),
        ("workspace_drive.document.find", workspace_drive_find),
        ("workspace_drive.health", workspace_drive_health),
    )
    writes = (
        ("workspace_drive.document.append_bounded", workspace_drive_append),
        ("workspace_drive.document.update_bounded", workspace_drive_update),
        ("workspace_drive.create_document", workspace_drive_create),
        ("workspace_drive.write_evidence", workspace_drive_append),
        ("workspace_drive.update_current_state", workspace_drive_append),
        ("workspace_drive.write_learning_candidate", workspace_drive_create),
        ("workspace_drive.write_memory_candidate", workspace_drive_create),
        ("workspace_drive.write_knowledge_candidate", workspace_drive_create),
    )
    return tuple(
        CapabilityDescriptorV1(capability_id, "READ_ONLY", adapt(handler))
        for capability_id, handler in read_only
    ) + tuple(
        CapabilityDescriptorV1(
            capability_id,
            "SOURCE_WRITE",
            adapt(handler),
            idempotency_class="STATEFUL_GOVERNED",
        )
        for capability_id, handler in writes
    )
