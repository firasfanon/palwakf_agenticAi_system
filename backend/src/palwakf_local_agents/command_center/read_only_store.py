from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import SAFETY_POSTURE

TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class ReadOnlyStoreError(ValueError):
    """Raised when a caller asks for a path or item outside the read-only contract."""


@dataclass(frozen=True)
class AllowedRoot:
    key: str
    path: Path


class LocalAgentsReadOnlyStore:
    """Allowlisted reader for local-agents Command Center V1.

    This class deliberately contains no write, child-process, database, network, Git,
    secrets, model-client, or task-execution behavior.
    """

    def __init__(self, project_root: str | Path):
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ReadOnlyStoreError(f"PROJECT_ROOT_NOT_FOUND={root}")
        self.project_root = root
        self.roots = {
            "inbox": AllowedRoot("inbox", root / "tasks" / "inbox"),
            "approved": AllowedRoot("approved", root / "tasks" / "approved"),
            "archived": AllowedRoot("archived", root / "tasks" / "archived"),
            "reviews": AllowedRoot("reviews", root / "audit" / "human_reviews"),
            "evidence": AllowedRoot("evidence", root / "output" / "evidence_manifests"),
            "evals": AllowedRoot("evals", root / "output" / "evals"),
            "references": AllowedRoot("references", root / "reference_sources" / "approved"),
        }

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().upper()

    def _safe_relative(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.project_root).as_posix()
        except ValueError as exc:
            raise ReadOnlyStoreError("PATH_OUTSIDE_PROJECT_ROOT") from exc

    @staticmethod
    def _timestamp(path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()

    def _metadata(self, path: Path, kind: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "relative_path": self._safe_relative(path),
            "modified_at": self._timestamp(path),
            "sha256": self._sha256(path),
            "size_bytes": path.stat().st_size,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReadOnlyStoreError(f"INVALID_JSON={path.name}") from exc
        if not isinstance(data, dict):
            raise ReadOnlyStoreError(f"JSON_OBJECT_REQUIRED={path.name}")
        return data

    @staticmethod
    def _summary_text(value: Any, maximum: int = 220) -> str:
        text = "" if value is None else str(value)
        return text if len(text) <= maximum else f"{text[:maximum - 1]}…"

    def _list_json(self, root_key: str) -> list[Path]:
        root = self.roots[root_key].path
        if not root.exists():
            return []
        return sorted((p for p in root.glob("*.json") if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)

    def list_tasks(self, queue: str | None = None) -> list[dict[str, Any]]:
        queues = [queue] if queue in {"inbox", "approved", "archived"} else ["inbox", "approved", "archived"]
        result: list[dict[str, Any]] = []
        for queue_name in queues:
            for path in self._list_json(queue_name):
                try:
                    task = self._read_json(path)
                except ReadOnlyStoreError:
                    continue
                result.append({
                    "queue": queue_name,
                    "task_id": str(task.get("task_id", path.stem)),
                    "title": self._summary_text(task.get("title", path.stem), 160),
                    "description": self._summary_text(task.get("description", ""), 260),
                    "status": str(task.get("status", "UNKNOWN")),
                    "risk": str(task.get("risk", "UNKNOWN")),
                    "autonomy": str(task.get("autonomy", "UNKNOWN")),
                    "requested_agent": str(task.get("requested_agent", "UNKNOWN")),
                    "human_approval_required": bool(task.get("human_approval_required", False)),
                    "metadata": self._metadata(path, "task"),
                })
        return result

    def get_task(self, task_id: str) -> dict[str, Any]:
        if not TASK_ID_PATTERN.fullmatch(task_id):
            raise ReadOnlyStoreError("INVALID_TASK_ID")
        matches: list[tuple[str, Path]] = []
        for queue in ("inbox", "approved", "archived"):
            candidate = self.roots[queue].path / f"{task_id}.json"
            if candidate.exists() and candidate.is_file():
                matches.append((queue, candidate))
        if len(matches) != 1:
            raise ReadOnlyStoreError("TASK_NOT_FOUND_OR_AMBIGUOUS")
        queue, path = matches[0]
        task = self._read_json(path)
        return {
            "queue": queue,
            "task": task,
            "metadata": self._metadata(path, "task"),
            "safety_posture": SAFETY_POSTURE,
            "execution_notice": "Execution requires a separate explicit authorization.",
        }

    def list_reviews(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for path in self._list_json("reviews"):
            try:
                record = self._read_json(path)
            except ReadOnlyStoreError:
                continue
            output.append({
                "review_id": str(record.get("review_id", path.stem)),
                "record_type": str(record.get("record_type", "HUMAN_REVIEW")),
                "task_id": str(record.get("task_id", "UNKNOWN")),
                "reviewer": str(record.get("reviewer", "UNKNOWN")),
                "decision": str(record.get("decision", record.get("review_decision", "UNKNOWN"))),
                "scope": str(record.get("approval_scope", record.get("review_scope", "UNKNOWN"))),
                "transition_status": str(record.get("transition_status", "COMPLETE")),
                "created_at": str(record.get("created_at_local", record.get("created_at", ""))),
                "metadata": self._metadata(path, "review"),
            })
        return output

    def list_evidence(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for key, label in (("evidence", "evidence_manifest"), ("evals", "deterministic_eval")):
            for path in self._list_json(key):
                try:
                    record = self._read_json(path)
                except ReadOnlyStoreError:
                    record = {}
                entries.append({
                    "category": label,
                    "id": str(record.get("run_id", record.get("eval_id", path.stem))),
                    "task_id": str(record.get("task_id", "")),
                    "status": str(record.get("status", record.get("final_result", record.get("result", "UNKNOWN")))),
                    "summary": self._summary_text(record.get("summary", record.get("purpose", "")), 220),
                    "metadata": self._metadata(path, label),
                })
        return sorted(entries, key=lambda item: item["metadata"]["modified_at"], reverse=True)

    def list_references(self) -> list[dict[str, Any]]:
        root = self.roots["references"].path
        if not root.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.name.lower()):
            # only readable, approved reference file metadata. Content remains unexposed in V1.
            items.append({
                "name": path.name,
                "metadata": self._metadata(path, "approved_reference"),
            })
        return items

    def agent_registry(self) -> list[dict[str, Any]]:
        # Registry baseline is intentionally static until a dedicated registry API is admitted.
        return [
            {"agent_id": "coordinator", "display_name_ar": "المنسق", "readiness": "BASELINE_ONLY", "allowed_scope": "L0_READ_ONLY"},
            {"agent_id": "sovereignty_reviewer", "display_name_ar": "مراجع السيادة", "readiness": "BASELINE_ONLY", "allowed_scope": "L0_READ_ONLY"},
            {"agent_id": "knowledge_researcher", "display_name_ar": "باحث المعرفة", "readiness": "BASELINE_ONLY", "allowed_scope": "L0_READ_ONLY"},
            {"agent_id": "documentation_handoff", "display_name_ar": "مساعد التوريث والتوثيق", "readiness": "PILOT_APPROVED_NOT_EXECUTED", "allowed_scope": "L0_READ_ONLY"},
        ]

    def governance(self) -> dict[str, Any]:
        files = []
        allowed_names = {
            "README_AR.md", "PROJECT_STATUS_AR.md", "PROJECT_STATUS_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_AR.md",
            "MANIFEST_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1.md", "MANIFEST_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3.md",
        }
        for name in sorted(allowed_names):
            candidate = self.project_root / name
            if candidate.exists() and candidate.is_file():
                files.append(self._metadata(candidate, "governance"))
        return {
            "core_runtime": "FROZEN",
            "core_11_line_output_contract": "UNCHANGED",
            "lifecycle_closure": "REV_C_ACCEPTED",
            "safety_posture": SAFETY_POSTURE,
            "approved_references": self.list_references(),
            "known_governance_files": files,
        }

    def dashboard(self) -> dict[str, Any]:
        tasks = self.list_tasks()
        approved = [x for x in tasks if x["queue"] == "approved"]
        archived = [x for x in tasks if x["queue"] == "archived"]
        inbox = [x for x in tasks if x["queue"] == "inbox"]
        reviews = self.list_reviews()
        evidence = self.list_evidence()
        return {
            "system_posture": {"label_ar": "واجهة قراءة ومراجعة فقط", **SAFETY_POSTURE},
            "counts": {
                "inbox": len(inbox),
                "approved": len(approved),
                "archived": len(archived),
                "reviews": len(reviews),
                "evidence": len(evidence),
            },
            "active_approved_tasks": approved,
            "latest_reviews": reviews[:5],
            "latest_evidence": evidence[:5],
            "open_risks": [
                "المهمة المعتمدة الحالية لم تُنفذ بعد وتحتاج تفويض تشغيل مستقل.",
                "الواجهة لا تمنح صلاحيات اعتماد أو تشغيل أو أرشفة في V1.",
                "توسعة بقية الأدوار تحتاج Pilots مستقلة ومراجعات بشرية.",
            ],
        }

    def system_health(self) -> dict[str, Any]:
        approved = self.list_tasks("approved")
        return {
            "health": "READ_ONLY_READY",
            "active_approved_task_count": len(approved),
            "active_approved_task_ids": [x["task_id"] for x in approved],
            "allowlisted_roots": {key: str(value.path.relative_to(self.project_root)).replace("\\", "/") for key, value in self.roots.items()},
            "safety_posture": SAFETY_POSTURE,
            "notes": [
                "وجود مهمة approved لا يعني أنها نُفذت.",
                "لا توجد مسارات HTTP للكتابة ضمن Command Center V1.",
            ],
        }
