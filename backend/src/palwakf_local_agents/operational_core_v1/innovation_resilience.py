from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .state_store import GovernedLocalStateStore


INNOVATION_SCHEMA = "palwakf.local_agents.innovation_resilience_identity.v1"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_\u0600-\u06FF]+")
_STOP = {
    "من", "في", "على", "إلى", "الى", "عن", "مع", "هذا", "هذه", "ذلك", "تلك", "ثم", "او", "أو",
    "the", "a", "an", "and", "or", "to", "of", "for", "with", "in", "on", "is", "are", "be",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def normalize_list(values: list[Any], limit: int) -> list[str]:
    result: list[str] = []
    for value in values:
        item = re.sub(r"\s+", " ", str(value).strip())[:180]
        if item and item.lower() not in {x.lower() for x in result}:
            result.append(item)
        if len(result) >= limit:
            break
    return result


def tokens(value: str) -> set[str]:
    return {item.lower() for item in _TOKEN_RE.findall(value) if len(item) > 1 and item.lower() not in _STOP}


def jaccard(a: list[str], b: list[str]) -> float:
    sa = {normalize(x) for x in a if normalize(x)}
    sb = {normalize(x) for x in b if normalize(x)}
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class InnovationResilienceManager:
    """Prepare-only innovation, deterministic resilience and design identity metadata."""

    def __init__(self, project_root: Path, state_store: GovernedLocalStateStore) -> None:
        self.project_root = project_root.resolve()
        self.store = state_store
        self.root = state_store.state_root
        self.reviews_path = self.root / "innovation_reviews.json"
        self.resilience_path = self.root / "resilience_state.json"
        self.identities_path = self.root / "project_identities.json"
        self._lock = threading.RLock()

    def initialize(self) -> None:
        self.store.initialize()
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            if not self.reviews_path.exists():
                self._write(self.reviews_path, {"schema": INNOVATION_SCHEMA, "reviews": [], "updated_at": utc_now()})
            if not self.resilience_path.exists():
                self._write(self.resilience_path, {
                    "schema": INNOVATION_SCHEMA,
                    "policy": {"max_consecutive_failures": 3, "automatic_retry": False, "duplicate_detection": True, "checkpoint_metadata_only": True},
                    "attempts": {}, "checkpoints": [], "last_context_check": None, "warnings": [], "updated_at": utc_now(),
                })
            if not self.identities_path.exists():
                self._write(self.identities_path, {"schema": INNOVATION_SCHEMA, "current_project_key": None, "identities": [], "updated_at": utc_now()})

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        os.replace(tmp, path)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _score_card(mode: str) -> dict[str, int]:
        cards = {
            "conservative": {"value": 3, "risk": 1, "complexity": 1, "ux_impact": 2, "performance_impact": 1},
            "balanced": {"value": 4, "risk": 2, "complexity": 3, "ux_impact": 4, "performance_impact": 3},
            "innovative": {"value": 5, "risk": 4, "complexity": 5, "ux_impact": 5, "performance_impact": 4},
        }
        return cards[mode]

    def prepare_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        review_id = f"irv_{uuid4().hex[:14]}"
        title = str(payload["title"]).strip()
        context = str(payload["context"]).strip()
        focus = str(payload.get("focus", "general"))
        constraints = normalize_list(payload.get("constraints", []), 20)
        evidence_refs = normalize_list(payload.get("evidence_refs", []), 20)
        alternatives = [
            {
                "alternative_id": f"{review_id}_conservative",
                "mode": "conservative",
                "title": "المسار المحافظ",
                "summary": f"تحسين {title} بأقل تغيير ممكن، مع إعادة استخدام العقود الحالية والحفاظ على قابلية الرجوع.",
                "delivery_shape": "تعديل محدود، أدلة واضحة، واعتماد بشري قبل أي انتقال.",
                "scores": self._score_card("conservative"),
                "required_gate": "HUMAN_INNOVATION_REVIEW_GATE",
                "status": "prepared_only",
            },
            {
                "alternative_id": f"{review_id}_balanced",
                "mode": "balanced",
                "title": "المسار المتوازن",
                "summary": f"إعادة تنظيم مستهدفة لـ{title} تجمع بين القيمة، سهولة الاستخدام، والحدود التشغيلية الحالية.",
                "delivery_shape": "شريحة رأسية قابلة للقياس مع نقاط تحقق ومقارنة قبل/بعد.",
                "scores": self._score_card("balanced"),
                "required_gate": "HUMAN_INNOVATION_REVIEW_GATE",
                "status": "prepared_only",
            },
            {
                "alternative_id": f"{review_id}_innovative",
                "mode": "innovative",
                "title": "المسار الابتكاري",
                "summary": f"تصور مختلف لـ{title} يختبر بنية أو تجربة جديدة، لكنه يبقى اقتراحًا غير منفذ حتى اعتماد مستقل.",
                "delivery_shape": "Prototype contract + risk register + rollback concept، دون تنفيذ أو نموذج.",
                "scores": self._score_card("innovative"),
                "required_gate": "HUMAN_INNOVATION_REVIEW_GATE",
                "status": "prepared_only",
            },
        ]
        review = {
            "review_id": review_id,
            "title": title,
            "context": context,
            "focus": focus,
            "constraints": constraints,
            "evidence_refs": evidence_refs,
            "alternatives": alternatives,
            "decision_summary": "تم إعداد ثلاثة مسارات للمقارنة؛ لم يُختر أي مسار ولم يحدث أي تنفيذ.",
            "assumptions": ["المسار الحالي prepare-only", "القرار النهائي بشري", "لا توجد صلاحية أدوات أو نموذج داخل المراجعة"],
            "risks": ["البديل الابتكاري أعلى تعقيدًا", "أي نقص في الأدلة يرفع القرار للمراجعة", "التقديرات وصفية وليست قياسات إنتاجية"],
            "uncertainty": "medium",
            "model_inference": "none",
            "execution_authority": "none",
            "status": "prepared_only",
            "created_at": utc_now(),
        }
        with self._lock:
            data = self._read(self.reviews_path)
            reviews = list(data.get("reviews", []))
            reviews.append(review)
            reviews = reviews[-100:]
            self._write(self.reviews_path, {"schema": INNOVATION_SCHEMA, "reviews": reviews, "updated_at": utc_now()})
        self.store.update_innovation_status(latest_review_id=review_id)
        self.store.append_event("innovation_review.prepared", {"review_id": review_id, "focus": focus, "alternative_count": 3})
        return deepcopy(review)

    def list_reviews(self, limit: int = 30) -> list[dict[str, Any]]:
        self.initialize()
        data = self._read(self.reviews_path)
        return deepcopy(data.get("reviews", [])[-max(1, min(limit, 100)):])

    def context_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        project_state = self.store.load_state()
        declared = str(payload.get("declared_goal") or "").strip()
        state_goal = ((project_state.get("current_goal") or {}).get("goal") or "").strip()
        goal = declared or state_goal
        action = str(payload["proposed_action"]).strip()
        goal_tokens = tokens(goal)
        action_tokens = tokens(action)
        matched = sorted(goal_tokens & action_tokens)
        score = round(len(matched) / max(1, len(goal_tokens)), 3) if goal_tokens else 0.0
        if not goal:
            decision = "NO_GOAL_CONTEXT"
            recommendation = "حضّر هدفًا أو مرر declared_goal قبل تقييم الانحراف."
        elif score >= 0.25:
            decision = "ALIGNED"
            recommendation = "يمكن متابعة التحضير ضمن بوابات المراجعة الحالية."
        elif score >= 0.10:
            decision = "WARNING"
            recommendation = "أضف مرجع المهمة أو وضّح الصلة بالهدف قبل اعتماد الخطة."
        else:
            decision = "HUMAN_REVIEW_REQUIRED"
            recommendation = "أوقف المسار التحضيري واطلب مراجعة بشرية للسياق؛ لا توجد إعادة محاولة تلقائية."
        result = {
            "check_id": f"ctx_{uuid4().hex[:12]}",
            "decision": decision,
            "alignment_score": score,
            "matched_keywords": matched[:20],
            "goal_keyword_count": len(goal_tokens),
            "action_keyword_count": len(action_tokens),
            "referenced_task_id": payload.get("referenced_task_id"),
            "recommendation": recommendation,
            "automatic_action": "none",
            "checked_at": utc_now(),
        }
        with self._lock:
            data = self._read(self.resilience_path)
            data["last_context_check"] = result
            if decision in {"WARNING", "HUMAN_REVIEW_REQUIRED"}:
                warnings = list(data.get("warnings", []))
                warnings.append({"type": "context_drift", "decision": decision, "check_id": result["check_id"], "created_at": utc_now()})
                data["warnings"] = warnings[-100:]
            data["updated_at"] = utc_now()
            self._write(self.resilience_path, data)
        self.store.append_event("resilience.context_checked", {"check_id": result["check_id"], "decision": decision, "score": score})
        return result

    def register_attempt(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        key = str(payload["operation_key"])
        fingerprint = normalize(payload["fingerprint"])
        outcome = str(payload["outcome"])
        with self._lock:
            data = self._read(self.resilience_path)
            attempts = dict(data.get("attempts", {}))
            current = dict(attempts.get(key, {}))
            duplicate = current.get("last_fingerprint") == fingerprint and bool(fingerprint)
            consecutive = int(current.get("consecutive_failures", 0))
            total = int(current.get("total_attempts", 0)) + 1
            if outcome == "failure":
                consecutive += 1
            elif outcome == "success":
                consecutive = 0
            status = "RECORDED"
            if outcome == "failure" and consecutive >= int(data.get("policy", {}).get("max_consecutive_failures", 3)):
                status = "ESCALATION_REQUIRED"
            elif duplicate and outcome == "failure":
                status = "DUPLICATE_FAILURE_WARNING"
            elif outcome == "failure":
                status = "REPLAN_REQUIRED"
            current.update({
                "operation_key": key,
                "total_attempts": total,
                "consecutive_failures": consecutive,
                "last_fingerprint": fingerprint,
                "last_outcome": outcome,
                "last_note": (payload.get("note") or "")[:500],
                "duplicate_detected": duplicate,
                "status": status,
                "automatic_retry_allowed": False,
                "updated_at": utc_now(),
            })
            attempts[key] = current
            data["attempts"] = attempts
            if status in {"ESCALATION_REQUIRED", "DUPLICATE_FAILURE_WARNING"}:
                warnings = list(data.get("warnings", []))
                warnings.append({"type": "attempt_guard", "operation_key": key, "status": status, "created_at": utc_now()})
                data["warnings"] = warnings[-100:]
            data["updated_at"] = utc_now()
            self._write(self.resilience_path, data)
        self.store.append_event("resilience.attempt_registered", {"operation_key": key, "outcome": outcome, "status": status, "consecutive_failures": consecutive})
        return deepcopy(current)

    def create_checkpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        project_state = self.store.load_state()
        identities = self._read(self.identities_path)
        reviews = self._read(self.reviews_path)
        tasks = list(project_state.get("tasks", []))
        checkpoint = {
            "checkpoint_id": f"chk_{uuid4().hex[:14]}",
            "label": str(payload["label"]).strip(),
            "reason": str(payload["reason"]).strip(),
            "state_revision": project_state.get("revision", 0),
            "goal_id": (project_state.get("current_goal") or {}).get("goal_id"),
            "review_status": (project_state.get("review") or {}).get("status"),
            "task_status_counts": ({status: sum(1 for task in tasks if task.get("status") == status) for status in {str(t.get("status")) for t in tasks}} if payload.get("include_task_statuses", True) else {}),
            "active_rule_count": sum(1 for item in self.store.list_rules() if item.get("enabled")),
            "current_project_key": identities.get("current_project_key"),
            "innovation_review_count": len(reviews.get("reviews", [])),
            "snapshot_kind": "metadata_only",
            "source_copy": "none",
            "database_snapshot": "none",
            "created_at": utc_now(),
        }
        with self._lock:
            data = self._read(self.resilience_path)
            checkpoints = list(data.get("checkpoints", []))
            checkpoints.append(checkpoint)
            data["checkpoints"] = checkpoints[-50:]
            data["updated_at"] = utc_now()
            self._write(self.resilience_path, data)
        self.store.update_innovation_status(checkpoint=checkpoint)
        self.store.append_event("resilience.checkpoint_created", {"checkpoint_id": checkpoint["checkpoint_id"], "state_revision": checkpoint["state_revision"]})
        return deepcopy(checkpoint)

    def get_resilience_state(self) -> dict[str, Any]:
        self.initialize()
        data = self._read(self.resilience_path)
        attempts = list(data.get("attempts", {}).values())
        return {
            **deepcopy(data),
            "summary": {
                "tracked_operations": len(attempts),
                "escalation_required": sum(1 for item in attempts if item.get("status") == "ESCALATION_REQUIRED"),
                "warning_count": len(data.get("warnings", [])),
                "checkpoint_count": len(data.get("checkpoints", [])),
            },
        }

    @staticmethod
    def _identity_payload(project_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        canonical = {
            "project_key": project_key,
            "project_name": str(payload["project_name"]).strip(),
            "domain": str(payload["domain"]).strip(),
            "target_audience": str(payload["target_audience"]).strip(),
            "brand_personality": normalize_list(payload.get("brand_personality", []), 6),
            "visual_keywords": normalize_list(payload.get("visual_keywords", []), 10),
            "color_direction": str(payload["color_direction"]).strip(),
            "typography_direction": str(payload["typography_direction"]).strip(),
            "density": payload.get("density", "balanced"),
            "motion_level": payload.get("motion_level", "subtle"),
            "accessibility_level": payload.get("accessibility_level", "enhanced"),
            "text_direction": payload.get("text_direction", "rtl"),
            "navigation_style": str(payload["navigation_style"]).strip(),
            "card_style": str(payload["card_style"]).strip(),
            "corner_style": str(payload["corner_style"]).strip(),
            "layout_signature": str(payload["layout_signature"]).strip(),
            "distinctive_traits": normalize_list(payload.get("distinctive_traits", []), 12),
        }
        fingerprint_payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        canonical["design_fingerprint"] = hashlib.sha256(fingerprint_payload).hexdigest().upper()
        return canonical

    @staticmethod
    def _similarity(candidate: dict[str, Any], existing: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
        weights = {
            "color_direction": 15,
            "typography_direction": 12,
            "density": 8,
            "motion_level": 6,
            "navigation_style": 15,
            "card_style": 15,
            "corner_style": 8,
            "layout_signature": 15,
        }
        score = 0.0
        conflicts: list[dict[str, Any]] = []
        for field, weight in weights.items():
            same = normalize(candidate.get(field)) == normalize(existing.get(field)) and bool(normalize(candidate.get(field)))
            if same:
                score += weight
                conflicts.append({"field": field, "weight": weight, "reason": "exact_match"})
        brand = jaccard(candidate.get("brand_personality", []), existing.get("brand_personality", []))
        visual = jaccard(candidate.get("visual_keywords", []), existing.get("visual_keywords", []))
        score += brand * 3
        score += visual * 3
        if brand >= 0.67:
            conflicts.append({"field": "brand_personality", "weight": round(brand * 3, 2), "reason": "high_overlap"})
        if visual >= 0.67:
            conflicts.append({"field": "visual_keywords", "weight": round(visual * 3, 2), "reason": "high_overlap"})
        return int(round(min(score, 100))), conflicts

    def similarity_check(self, project_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        candidate = self._identity_payload(project_key, payload)
        data = self._read(self.identities_path)
        comparisons = []
        for existing in data.get("identities", []):
            if existing.get("project_key") == project_key:
                continue
            score, conflicts = self._similarity(candidate, existing)
            comparisons.append({"project_key": existing.get("project_key"), "project_name": existing.get("project_name"), "similarity_score": score, "conflicts": conflicts})
        comparisons.sort(key=lambda item: item["similarity_score"], reverse=True)
        highest = comparisons[0] if comparisons else None
        max_score = highest["similarity_score"] if highest else 0
        if max_score >= 70:
            status = "DIFFERENTIATION_REQUIRED"
            required = [item["field"] for item in highest.get("conflicts", [])[:6]]
        elif max_score >= 45:
            status = "REVIEW_RECOMMENDED"
            required = [item["field"] for item in highest.get("conflicts", [])[:4]]
        else:
            status = "DISTINCT_ENOUGH"
            required = []
        return {
            "candidate": candidate,
            "compared_project_count": len(comparisons),
            "highest_similarity": highest,
            "similarity_score": max_score,
            "status": status,
            "required_differentiation": required,
            "method": "deterministic_weighted_metadata_v1",
            "vector_db": "none",
            "model_inference": "none",
        }

    def upsert_identity(self, project_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        check = self.similarity_check(project_key, payload)
        identity = dict(check["candidate"])
        identity.update({
            "similarity_status": check["status"],
            "similarity_score": check["similarity_score"],
            "required_differentiation": check["required_differentiation"],
            "status": "prepared_only",
            "updated_at": utc_now(),
        })
        with self._lock:
            data = self._read(self.identities_path)
            identities = list(data.get("identities", []))
            replaced = False
            for idx, existing in enumerate(identities):
                if existing.get("project_key") == project_key:
                    identities[idx] = identity
                    replaced = True
                    break
            if not replaced:
                identities.append(identity)
            data = {"schema": INNOVATION_SCHEMA, "current_project_key": project_key, "identities": identities[-100:], "updated_at": utc_now()}
            self._write(self.identities_path, data)
        self.store.update_innovation_status(identity_status=check["status"])
        self.store.append_event("project_identity.upserted", {"project_key": project_key, "similarity_status": check["status"], "similarity_score": check["similarity_score"]})
        return {"identity": deepcopy(identity), "anti_similarity": check, "execution_effect": "none"}

    def list_identities(self) -> dict[str, Any]:
        self.initialize()
        return deepcopy(self._read(self.identities_path))

    def dashboard(self) -> dict[str, Any]:
        self.initialize()
        state = self.store.load_state()
        reviews = self.list_reviews(5)
        resilience = self.get_resilience_state()
        identities = self.list_identities()
        current_key = identities.get("current_project_key")
        current_identity = next((item for item in identities.get("identities", []) if item.get("project_key") == current_key), None)
        tasks = state.get("tasks", [])
        return {
            "schema": INNOVATION_SCHEMA,
            "result": "PASS",
            "mode": "prepare_only",
            "current_goal": state.get("current_goal"),
            "current_phase": next((step.get("phase") for step in state.get("plan_steps", []) if step.get("status") != "completed"), None),
            "pending_review_count": sum(1 for task in tasks if task.get("status") in {"ready_for_review", "draft", "returned"}),
            "last_checkpoint": (state.get("continuity") or {}).get("last_checkpoint"),
            "active_rule_count": sum(1 for item in self.store.list_rules() if item.get("enabled")),
            "latest_innovation_review": reviews[-1] if reviews else None,
            "resilience_summary": resilience.get("summary"),
            "last_context_check": resilience.get("last_context_check"),
            "current_identity": current_identity,
            "warnings": resilience.get("warnings", [])[-10:],
            "boundaries": {
                "model_inference": "none",
                "shell": "blocked",
                "git": "blocked",
                "code_execution": "blocked",
                "self_apply": "blocked",
                "vector_db": "none",
                "automatic_retry": False,
                "state_write": "runtime_state/operational_core_v1_only",
            },
        }
