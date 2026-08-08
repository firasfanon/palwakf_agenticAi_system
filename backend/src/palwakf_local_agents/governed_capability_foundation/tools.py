from __future__ import annotations

import re
from collections import Counter
from typing import Any


def _terms(text: str) -> list[str]:
    return [item.lower() for item in re.findall(r"[A-Za-z\u0600-\u06ff0-9_]{2,}", text or "")]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[.!؟\n]+", text or "") if part.strip()]


def _top_terms(text: str, limit: int = 8) -> list[str]:
    ignored = {"the", "and", "for", "with", "this", "that", "من", "في", "على", "إلى", "عن", "هذا", "هذه"}
    counts = Counter(term for term in _terms(text) if term not in ignored)
    return [term for term, _ in counts.most_common(limit)]


def deterministic_tool(tool_name: str, text: str) -> dict[str, Any]:
    clean = str(text or "").strip()
    if tool_name == "summarize":
        sentences = _sentences(clean)
        return {
            "kind": "DETERMINISTIC_SUMMARY",
            "sentence_count": len(sentences),
            "summary_points": sentences[:3],
            "model_execution": "NONE",
            "external_access": "NONE",
        }
    if tool_name == "classify":
        lowered = clean.lower()
        labels = []
        if any(token in lowered for token in ["evidence", "دليل", "أدلة"]): labels.append("evidence")
        if any(token in lowered for token in ["task", "مهمة", "مهام"]): labels.append("task_planning")
        if any(token in lowered for token in ["project", "مشروع", "مشاريع"]): labels.append("project_management")
        if any(token in lowered for token in ["research", "بحث", "أبحاث"]): labels.append("research")
        return {
            "kind": "DETERMINISTIC_CLASSIFICATION",
            "labels": labels or ["general_prepare"],
            "top_terms": _top_terms(clean),
            "model_execution": "NONE",
            "external_access": "NONE",
        }
    if tool_name == "extract_terms":
        return {
            "kind": "DETERMINISTIC_TERM_EXTRACTION",
            "terms": _top_terms(clean, limit=20),
            "model_execution": "NONE",
            "external_access": "NONE",
        }
    if tool_name == "runbook":
        return {
            "kind": "DETERMINISTIC_RUNBOOK_DRAFT",
            "objective": clean,
            "phases": [
                "Confirm workspace scope and policy.",
                "Prepare a bounded read-only or prepare-only output.",
                "Collect evidence and obtain human review.",
                "Do not execute shell, Git, deployment, or external operations.",
            ],
            "model_execution": "NONE",
            "external_access": "NONE",
        }
    raise KeyError("DETERMINISTIC_TOOL_NOT_FOUND")
