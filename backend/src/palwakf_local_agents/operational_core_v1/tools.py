from __future__ import annotations

from pathlib import Path
from typing import Any

from .codebase_index import CodebaseIndexer


TOOL_REGISTRY: list[dict[str, Any]] = [
    {
        "tool_id": "project_summary",
        "name_ar": "ملخص المشروع",
        "mode": "read_only",
        "description": "يعيد ملخصًا حيًا للبنية المفهرسة دون قراءة محتوى الملفات للمستخدم.",
    },
    {
        "tool_id": "route_index",
        "name_ar": "فهرس المسارات",
        "mode": "read_only",
        "description": "يعرض مسارات FastAPI ومسارات واجهة Agent Console المكتشفة.",
    },
    {
        "tool_id": "component_index",
        "name_ar": "فهرس المكونات",
        "mode": "read_only",
        "description": "يعرض مكونات TypeScript/React المكتشفة بقراءة المصدر فقط.",
    },
    {
        "tool_id": "symbol_index",
        "name_ar": "فهرس الرموز",
        "mode": "read_only",
        "description": "يعرض الدوال والكلاسات في Python ضمن النطاق المسموح.",
    },
    {
        "tool_id": "docs_index",
        "name_ar": "فهرس الوثائق",
        "mode": "read_only",
        "description": "يعرض وثائق Markdown وعناوينها الرئيسية.",
    },
    {
        "tool_id": "file_metadata",
        "name_ar": "بيانات الملف الوصفية",
        "mode": "read_only",
        "description": "يعرض الحجم والامتداد وSHA-256 دون إرجاع المحتوى.",
    },
]


class GovernedReadOnlyToolRuntime:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.indexer = CodebaseIndexer(self.project_root)

    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(item, executable=False, side_effect="none") for item in TOOL_REGISTRY]

    def invoke(self, tool_id: str, *, path: str | None = None, limit: int = 100) -> dict[str, Any]:
        if tool_id not in {item["tool_id"] for item in TOOL_REGISTRY}:
            raise KeyError(tool_id)
        if tool_id == "file_metadata":
            if not path:
                raise ValueError("PATH_REQUIRED")
            result = self.indexer.metadata_for(path)
        else:
            index = self.indexer.build(detail_limit=limit)
            if tool_id == "project_summary":
                result = {"summary": index["summary"], "scope": index["scope"], "limits": index["limits"]}
            elif tool_id == "route_index":
                result = {"routes": index["routes"], "count": len(index["routes"])}
            elif tool_id == "component_index":
                result = {"components": index["components"], "count": len(index["components"])}
            elif tool_id == "symbol_index":
                result = {"symbols": index["symbols"], "count": len(index["symbols"])}
            elif tool_id == "docs_index":
                result = {"documents": index["documents"], "count": len(index["documents"])}
            else:
                raise KeyError(tool_id)
        return {
            "tool_id": tool_id,
            "mode": "read_only",
            "side_effect": "none",
            "execution_authority": "read_only_contract",
            "result": result,
        }
