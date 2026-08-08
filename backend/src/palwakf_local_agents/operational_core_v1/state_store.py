from __future__ import annotations

import json
import os
import re
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


STATE_SCHEMA = "palwakf.local_agents.operational_core.v1"
_ALLOWED_RULE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,79}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "human_authority",
        "title": "القرار النهائي للمستخدم",
        "statement": "لا ينتقل أي مسار من الخطة إلى التنفيذ دون تفويض مستقل وصريح.",
        "category": "governance",
        "enabled": True,
        "source": "PROJECT_REALITY_AND_GOVERNING_CHARTER_V1",
    },
    {
        "rule_id": "goal_to_plan_first",
        "title": "الهدف يتحول إلى خطة أولًا",
        "statement": "كل هدف جديد يمر بمرحلة Spec/Plan ومسودات قابلة للمراجعة قبل أي تفعيل.",
        "category": "workflow",
        "enabled": True,
        "source": "GOAL_TO_PLAN_TOOL_SELECTION_V1",
    },
    {
        "rule_id": "operational_ux_first",
        "title": "Operational UX First",
        "statement": "الصفحات اليومية بسيطة وتشغيلية، وتبقى تفاصيل الحوكمة في الصفحات الفرعية.",
        "category": "ux",
        "enabled": True,
        "source": "OPERATIONAL_UX_REFINEMENT_V1",
    },
    {
        "rule_id": "no_hidden_execution",
        "title": "لا تنفيذ خفي",
        "statement": "كل أداة تعلن نوع أثرها وحدودها، ولا يوجد Shell أو Git أو Model أو Code execution في هذه المرحلة.",
        "category": "safety",
        "enabled": True,
        "source": "GOVERNING_CHARTER_V1",
    },
    {
        "rule_id": "full_stack_vertical_slices",
        "title": "التطوير الرأسي Full-stack",
        "statement": "تُفضّل الشرائح الرأسية التي تربط العقد الخلفي والواجهة والفحص بدل دفعات واجهة منفصلة.",
        "category": "engineering",
        "enabled": True,
        "source": "USER_DIRECTION_20260710",
    },
    {
        "rule_id": "explainable_decision_summary",
        "title": "تفسير القرار دون كشف التفكير الداخلي",
        "statement": "تُعرض الافتراضات والأدلة والمخاطر والشك، ولا تُعرض سلسلة التفكير الداخلية الخام.",
        "category": "trust",
        "enabled": True,
        "source": "INNOVATION_RESILIENCE_LAYER_V1",
    },
    {
        "rule_id": "no_automatic_retry_loop",
        "title": "لا حلقات إعادة تلقائية",
        "statement": "بعد تكرار الفشل تُرفع الحالة للمراجعة البشرية بدل إعادة المحاولة بلا حد.",
        "category": "resilience",
        "enabled": True,
        "source": "INNOVATION_RESILIENCE_LAYER_V1",
    },
]


class GovernedLocalStateStore:
    """Project-local JSON/JSONL state only. It never mutates source code or databases."""

    def __init__(self, project_root: Path, state_root: Path | None = None) -> None:
        self.project_root = project_root.resolve()
        configured = os.getenv("PALWAKF_LOCAL_AGENTS_STATE_ROOT", "").strip()
        chosen = state_root or (Path(configured) if configured else self.project_root / "runtime_state" / "operational_core_v1")
        self.state_root = chosen.resolve()
        self.state_path = self.state_root / "project_state.json"
        self.events_path = self.state_root / "events.jsonl"
        self.rules_path = self.state_root / "standing_rules.json"
        self._lock = threading.RLock()

    def initialize(self) -> None:
        with self._lock:
            self.state_root.mkdir(parents=True, exist_ok=True)
            if not self.state_path.exists():
                self._atomic_json_write(self.state_path, self._new_state())
            else:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
                changed = self._migrate_state(state)
                if changed:
                    self._atomic_json_write(self.state_path, state)
            if not self.rules_path.exists():
                self._atomic_json_write(self.rules_path, {"schema": STATE_SCHEMA, "rules": DEFAULT_RULES, "updated_at": utc_now()})
            else:
                self._merge_default_rules()
            if not self.events_path.exists():
                self.events_path.write_text("", encoding="utf-8")

    def _new_state(self) -> dict[str, Any]:
        return {
            "schema": STATE_SCHEMA,
            "revision": 0,
            "updated_at": utc_now(),
            "current_goal": None,
            "plan_steps": [],
            "tasks": [],
            "review": {"status": "not_started", "accepted_task_count": 0},
            "continuity": {
                "snapshot_status": "available",
                "last_checkpoint": None,
                "context_drift_guard": "enabled",
            },
            "innovation_layer": {
                "status": "prepare_only",
                "latest_review_id": None,
                "project_identity_status": "not_configured",
                "resilience_guard": "enabled",
            },
            "execution": {
                "authority": "none",
                "model": "none",
                "pilot": "not_executed",
                "shell": "blocked",
                "git": "blocked",
                "code_execution": "blocked",
                "self_apply": "blocked",
            },
        }

    @staticmethod
    def _migrate_state(state: dict[str, Any]) -> bool:
        changed = False
        defaults = {
            "schema": STATE_SCHEMA,
            "revision": 0,
            "updated_at": utc_now(),
            "current_goal": None,
            "plan_steps": [],
            "tasks": [],
            "review": {"status": "not_started", "accepted_task_count": 0},
            "continuity": {"snapshot_status": "available", "last_checkpoint": None, "context_drift_guard": "enabled"},
            "innovation_layer": {"status": "prepare_only", "latest_review_id": None, "project_identity_status": "not_configured", "resilience_guard": "enabled"},
            "execution": {"authority": "none", "model": "none", "pilot": "not_executed", "shell": "blocked", "git": "blocked", "code_execution": "blocked", "self_apply": "blocked"},
        }
        for key, value in defaults.items():
            if key not in state:
                state[key] = deepcopy(value)
                changed = True
        for key, value in defaults["continuity"].items():
            if key not in state["continuity"]:
                state["continuity"][key] = value
                changed = True
        for key, value in defaults["innovation_layer"].items():
            if key not in state["innovation_layer"]:
                state["innovation_layer"][key] = value
                changed = True
        return changed

    def _merge_default_rules(self) -> None:
        data = json.loads(self.rules_path.read_text(encoding="utf-8"))
        rules = list(data.get("rules", []))
        existing = {item.get("rule_id") for item in rules}
        changed = False
        for rule in DEFAULT_RULES:
            if rule["rule_id"] not in existing:
                rules.append(deepcopy(rule))
                changed = True
        if changed:
            self._atomic_json_write(self.rules_path, {"schema": STATE_SCHEMA, "rules": rules, "updated_at": utc_now()})

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        os.replace(tmp, path)

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {"event_id": f"evt_{uuid4().hex}", "event_type": event_type, "created_at": utc_now(), "payload": payload}
        with self.events_path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.initialize()
        with self._lock:
            self._append_event(event_type, payload)

    def load_state(self) -> dict[str, Any]:
        self.initialize()
        with self._lock:
            return json.loads(self.state_path.read_text(encoding="utf-8"))

    def save_state(self, state: dict[str, Any], event_type: str, event_payload: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        with self._lock:
            state = deepcopy(state)
            self._migrate_state(state)
            state["revision"] = int(state.get("revision", 0)) + 1
            state["updated_at"] = utc_now()
            self._atomic_json_write(self.state_path, state)
            self._append_event(event_type, event_payload)
            return deepcopy(state)

    def update_innovation_status(self, *, latest_review_id: str | None = None, identity_status: str | None = None, checkpoint: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self.load_state()
        layer = state.setdefault("innovation_layer", {})
        if latest_review_id is not None:
            layer["latest_review_id"] = latest_review_id
        if identity_status is not None:
            layer["project_identity_status"] = identity_status
        if checkpoint is not None:
            state.setdefault("continuity", {})["last_checkpoint"] = checkpoint
        return self.save_state(state, "innovation_layer.state_updated", {"latest_review_id": latest_review_id, "identity_status": identity_status, "checkpoint_id": checkpoint.get("checkpoint_id") if checkpoint else None})

    def prepare_goal(self, request: dict[str, Any]) -> dict[str, Any]:
        state = self.load_state()
        goal_id = f"goal_{uuid4().hex[:12]}"
        goal = {
            "goal_id": goal_id,
            "goal": request["goal"].strip(),
            "project_type": request.get("project_type", "full_stack"),
            "target_user": request.get("target_user", "internal_user"),
            "priority": request.get("priority", "normal"),
            "constraints": [str(x).strip()[:300] for x in request.get("constraints", []) if str(x).strip()][:20],
            "status": "prepared",
            "created_at": utc_now(),
        }
        phases = [
            ("spec", "تحديد النطاق والعقود", "spec-driven-development", "SPEC_REVIEW_GATE", "وثيقة نطاق وعقود أولية"),
            ("plan", "تفكيك الهدف إلى خطة", "planning-and-task-breakdown", "PLAN_REVIEW_GATE", "خطة مرتبة مع التبعيات"),
            ("build", "تحضير مهام البناء", "incremental-implementation", "BUILD_AUTHORIZATION_GATE", "مسودات بناء فقط — لا تنفيذ"),
            ("verify", "تحضير الفحوص", "test-driven-development", "VERIFY_EVIDENCE_GATE", "خطة اختبارات وأدلة متوقعة"),
            ("review", "مراجعة الخطة والمخاطر", "code-review-and-quality", "HUMAN_REVIEW_GATE", "قرار قبول كخطة أو إرجاع"),
            ("ship", "تحضير متطلبات الإطلاق", "shipping-and-launch", "RELEASE_AUTHORIZATION_GATE", "قائمة جاهزية مستقبلية فقط"),
        ]
        plan_steps = []
        tasks = []
        for order, (phase, title, skill, gate, expected) in enumerate(phases, start=1):
            step_id = f"step_{order:02d}_{uuid4().hex[:8]}"
            task_id = f"task_{uuid4().hex[:12]}"
            plan_steps.append({"step_id": step_id, "order": order, "phase": phase, "title": title, "skill": skill, "gate": gate, "expected_output": expected, "status": "prepared_only"})
            tasks.append({"task_id": task_id, "goal_id": goal_id, "step_id": step_id, "title": title, "status": "draft", "skill": skill, "gate": gate, "expected_output": expected, "execution_authority": "none", "updated_at": utc_now()})
        state["current_goal"] = goal
        state["plan_steps"] = plan_steps
        state["tasks"] = tasks
        state["review"] = {"status": "draft", "accepted_task_count": 0}
        state["continuity"]["last_checkpoint"] = {"checkpoint_id": f"chk_{uuid4().hex[:12]}", "type": "goal_prepared", "created_at": utc_now()}
        return self.save_state(state, "goal.prepared", {"goal_id": goal_id, "task_count": len(tasks)})

    def transition_task(self, task_id: str, action: str, note: str | None = None) -> dict[str, Any]:
        mapping = {"ready_for_review": "ready_for_review", "accepted_as_plan": "accepted_as_plan", "returned_to_draft": "returned"}
        if action not in mapping:
            raise ValueError("UNSUPPORTED_TASK_TRANSITION")
        state = self.load_state()
        found = None
        for task in state.get("tasks", []):
            if task.get("task_id") == task_id:
                found = task
                task["status"] = mapping[action]
                task["review_note"] = (note or "")[:500]
                task["updated_at"] = utc_now()
                break
        if found is None:
            raise KeyError(task_id)
        accepted = sum(1 for task in state.get("tasks", []) if task.get("status") == "accepted_as_plan")
        ready = sum(1 for task in state.get("tasks", []) if task.get("status") == "ready_for_review")
        state["review"] = {"status": "accepted_as_plan" if accepted and accepted == len(state.get("tasks", [])) else ("ready_for_review" if ready else "in_progress"), "accepted_task_count": accepted}
        state["continuity"]["last_checkpoint"] = {"checkpoint_id": f"chk_{uuid4().hex[:12]}", "type": "task_transition", "task_id": task_id, "created_at": utc_now()}
        return self.save_state(state, "task.transitioned", {"task_id": task_id, "action": action})

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        self.initialize()
        limit = max(1, min(int(limit), 500))
        lines = self.events_path.read_text(encoding="utf-8").splitlines()
        result = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    def list_rules(self) -> list[dict[str, Any]]:
        self.initialize()
        with self._lock:
            data = json.loads(self.rules_path.read_text(encoding="utf-8"))
            return deepcopy(data.get("rules", []))

    def upsert_rule(self, rule_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not _ALLOWED_RULE_ID.fullmatch(rule_id):
            raise ValueError("INVALID_RULE_ID")
        self.initialize()
        with self._lock:
            data = json.loads(self.rules_path.read_text(encoding="utf-8"))
            rules = list(data.get("rules", []))
            item = {"rule_id": rule_id, "title": str(payload["title"]).strip(), "statement": str(payload["statement"]).strip(), "category": str(payload.get("category", "engineering")).strip(), "enabled": bool(payload.get("enabled", True)), "source": "LOCAL_OPERATOR", "updated_at": utc_now()}
            replaced = False
            for idx, current in enumerate(rules):
                if current.get("rule_id") == rule_id:
                    rules[idx] = item
                    replaced = True
                    break
            if not replaced:
                rules.append(item)
            data = {"schema": STATE_SCHEMA, "rules": rules, "updated_at": utc_now()}
            self._atomic_json_write(self.rules_path, data)
            self._append_event("standing_rule.upserted", {"rule_id": rule_id, "enabled": item["enabled"]})
            return deepcopy(item)
