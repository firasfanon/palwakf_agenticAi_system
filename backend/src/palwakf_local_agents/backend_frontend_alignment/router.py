from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, validator

ToolState = Literal["approved", "deferred", "blocked"]
TaskDraftState = Literal["prepared_for_human_review", "not_persisted"]


APPROVED_TOOLS: list[dict[str, Any]] = [
    {
        "tool_id": "tool_registry",
        "name_ar": "سجل الأدوات المحلي",
        "state": "approved",
        "authority": "read_only_metadata",
        "description_ar": "يعرض الأدوات وحالتها وحدودها دون تشغيلها.",
        "blocked_actions": ["shell", "git", "model_execution", "network", "db_write", "platform_mutation"],
    },
    {
        "tool_id": "task_drafting",
        "name_ar": "تحضير مسودة مهمة",
        "state": "approved",
        "authority": "prepare_only_no_persistence",
        "description_ar": "ينتج مسودة مهمة منظمة للمراجعة البشرية ولا يحفظها في قاعدة بيانات.",
        "blocked_actions": ["execute_task", "dispatch_agent", "model_execution", "db_write"],
    },
    {
        "tool_id": "project_reader",
        "name_ar": "قارئ المشروع المحلي",
        "state": "approved",
        "authority": "read_only_workspace_scoped",
        "description_ar": "يقرأ بنية المشروع والمسارات والملفات الرئيسية ضمن حدود workspace فقط.",
        "blocked_actions": ["write_file", "shell", "git", "model_execution", "network", "platform_mutation"],
    },
    {
        "tool_id": "route_api_reader",
        "name_ar": "قارئ المسارات والعقود",
        "state": "approved",
        "authority": "read_only_metadata",
        "description_ar": "يعرض Matrix للمسارات والعقود المتاحة للواجهة.",
        "blocked_actions": ["route_mutation", "api_write", "external_call"],
    },
    {
        "tool_id": "evidence_summarizer",
        "name_ar": "ملخص الأدلة",
        "state": "approved",
        "authority": "read_only_summary",
        "description_ar": "يلخص الأدلة الموجودة فقط دون إنشاء ترقية أو تعديل مصدر.",
        "blocked_actions": ["baseline_promotion", "source_write", "db_write"],
    },
]

DEFERRED_TOOLS: list[dict[str, Any]] = [
    {"tool_id": "document_reader", "name_ar": "قارئ المستندات", "state": "deferred", "revisit_gate": "DOCUMENT_READER_READ_ONLY_GATE_V1"},
    {"tool_id": "vector_memory", "name_ar": "ذاكرة متجهة Chroma/Lance/Qdrant", "state": "deferred", "revisit_gate": "MEMORY_ARCHITECTURE_GATE_V1"},
    {"tool_id": "langgraph_orchestration", "name_ar": "تنسيق LangGraph", "state": "deferred", "revisit_gate": "ORCHESTRATION_GATE_V1"},
    {"tool_id": "web_search", "name_ar": "بحث ويب SearXNG", "state": "deferred", "revisit_gate": "WEB_SEARCH_PRIVACY_GATE_V1"},
    {"tool_id": "ocr", "name_ar": "OCR", "state": "deferred", "revisit_gate": "DOCUMENT_MULTIMODAL_GATE_V1"},
    {"tool_id": "whisper", "name_ar": "تحويل الصوت إلى نص", "state": "deferred", "revisit_gate": "AUDIO_PROCESSING_GATE_V1"},
    {"tool_id": "docker_code_sandbox", "name_ar": "Code Sandbox", "state": "deferred", "revisit_gate": "CONTROLLED_CODE_EXECUTION_GATE_V1"},
]

BLOCKED_TOOLS: list[dict[str, Any]] = [
    {"tool_id": "shell", "name_ar": "Shell", "state": "blocked", "reason_ar": "مرفوض حاليًا لحماية الجهاز والمصدر."},
    {"tool_id": "git", "name_ar": "Git", "state": "blocked", "reason_ar": "لا pull/push/commit تلقائي."},
    {"tool_id": "code_execution", "name_ar": "تنفيذ الأكواد", "state": "blocked", "reason_ar": "يحتاج Sandbox مستقل لاحقًا."},
    {"tool_id": "model_execution", "name_ar": "تشغيل النموذج", "state": "blocked", "reason_ar": "مرفوض حتى تفويض Pilot مستقل."},
    {"tool_id": "pilot_execution", "name_ar": "Pilot", "state": "blocked", "reason_ar": "غير منفذ في هذه المرحلة."},
    {"tool_id": "agent_self_apply", "name_ar": "تطبيق ذاتي", "state": "blocked", "reason_ar": "كل Apply يحتاج تفويض بشري."},
    {"tool_id": "platform_mutation", "name_ar": "تعديل المنصة", "state": "blocked", "reason_ar": "خارج نطاق Local Agents."},
    {"tool_id": "uncontrolled_db_write", "name_ar": "كتابة قاعدة غير محكومة", "state": "blocked", "reason_ar": "لا كتابة DB دون عقد محلي واضح."},
]

ASSISTANTS: list[dict[str, Any]] = [
    {"agent_id": "coordinator", "name_ar": "المساعد المنسق العام", "category": "operational", "approved_tools": ["tool_registry", "task_drafting", "evidence_summarizer"]},
    {"agent_id": "task_analyst", "name_ar": "مساعد تحليل المهام", "category": "operational", "approved_tools": ["task_drafting", "tool_registry"]},
    {"agent_id": "project_reader", "name_ar": "مساعد قراءة المشروع", "category": "engineering", "approved_tools": ["project_reader", "route_api_reader"]},
    {"agent_id": "backend_reader", "name_ar": "قارئ الباك إند", "category": "engineering", "approved_tools": ["route_api_reader", "project_reader"]},
    {"agent_id": "frontend_designer", "name_ar": "مساعد الواجهة الأمامية", "category": "engineering", "approved_tools": ["tool_registry", "task_drafting", "project_reader"]},
    {"agent_id": "uat_tester", "name_ar": "مساعد الفحص والاختبار", "category": "engineering", "approved_tools": ["route_api_reader", "evidence_summarizer"]},
    {"agent_id": "safety_governor", "name_ar": "مساعد السلامة والحوكمة", "category": "governance", "approved_tools": ["tool_registry", "evidence_summarizer"]},
    {"agent_id": "evidence_baseline_keeper", "name_ar": "مساعد الأدلة والـBaseline", "category": "governance", "approved_tools": ["evidence_summarizer"]},
    {"agent_id": "documentation_handoff", "name_ar": "مساعد التوثيق والتوريث", "category": "governance", "approved_tools": ["evidence_summarizer", "task_drafting"]},
    {"agent_id": "error_triage_agent", "name_ar": "مساعد إصلاح الأخطاء", "category": "operational", "approved_tools": ["route_api_reader", "project_reader", "task_drafting"]},
    {"agent_id": "ux_reviewer", "name_ar": "مساعد تجربة المستخدم", "category": "engineering", "approved_tools": ["task_drafting", "tool_registry"]},
    {"agent_id": "local_model_manager", "name_ar": "مساعد إدارة النموذج المحلي", "category": "local_ai", "approved_tools": ["tool_registry"], "model_execution": "blocked"},
]


class TaskDraftPrepareRequest(BaseModel):
    assistant_id: str = Field(min_length=2, max_length=80)
    workspace_id: str = Field(default="local-dev", min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=3, max_length=2000)
    priority: Literal["low", "normal", "high"] = "normal"
    notes: str | None = Field(default=None, max_length=2000)

    @validator("assistant_id", "workspace_id")
    def safe_identifier(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:/")
        if any(ch not in allowed for ch in value):
            raise ValueError("UNSAFE_IDENTIFIER")
        if ".." in value or "\\" in value:
            raise ValueError("PATH_TRAVERSAL_BLOCKED")
        return value


class PreparedTaskDraft(BaseModel):
    draft_id: str
    state: TaskDraftState
    assistant_id: str
    workspace_id: str
    title: str
    objective: str
    priority: str
    allowed_tools: list[str]
    blocked_actions: list[str]
    review_required: bool
    persistence: Literal["none", "browser_local_storage_only"]
    execution_authority: Literal["none"]
    created_at: str
    next_step_ar: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _assistant(agent_id: str) -> dict[str, Any] | None:
    for item in ASSISTANTS:
        if item["agent_id"] == agent_id:
            return item
    return None


def build_router(*, project_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api/v1/backend-frontend-alignment", tags=["backend-frontend-alignment"])

    @router.get("/health")
    def health() -> dict[str, Any]:
        return {
            "result": "PASS",
            "service": "backend_frontend_alignment_v1",
            "mode": "approved_tools_only",
            "read_only": True,
            "prepare_only": True,
            "source_root_bound": str(project_root),
            "shell": "blocked",
            "git": "blocked",
            "model_execution": "blocked",
            "pilot_execution": "not_executed",
            "database_write": "none",
            "external_network": "none",
            "timestamp": _now(),
        }

    @router.get("/tool-registry")
    def tool_registry() -> dict[str, Any]:
        return {
            "result": "PASS",
            "policy": "APPROVED_TOOLS_ONLY",
            "approved": APPROVED_TOOLS,
            "deferred": DEFERRED_TOOLS,
            "blocked": BLOCKED_TOOLS,
            "counts": {
                "approved": len(APPROVED_TOOLS),
                "deferred": len(DEFERRED_TOOLS),
                "blocked": len(BLOCKED_TOOLS),
            },
        }

    @router.get("/assistants")
    def assistants() -> dict[str, Any]:
        return {
            "result": "PASS",
            "assistants": ASSISTANTS,
            "mapping_authority": "metadata_only_no_execution",
        }

    @router.get("/frontend-contract")
    def frontend_contract() -> dict[str, Any]:
        return {
            "result": "PASS",
            "accepted_frontend_stage": "FRONTEND_MEGA_OPERATIONAL_WORKSPACE_V1_VISUALLY_ACCEPTED",
            "current_backend_alignment": "BACKEND_FRONTEND_ALIGNMENT_V1_APPROVED_TOOLS_ONLY",
            "supported_ui_surfaces": [
                "/agent-console/",
                "/agent-console/tasks",
                "/agent-console/tools",
                "/agent-console/projects",
                "/agent-console/diagnostics",
                "/agent-console/pilot-control",
            ],
            "supported_api_surfaces": [
                "/api/v1/backend-frontend-alignment/health",
                "/api/v1/backend-frontend-alignment/tool-registry",
                "/api/v1/backend-frontend-alignment/assistants",
                "/api/v1/backend-frontend-alignment/task-drafts/prepare",
                "/api/v1/backend-frontend-alignment/deferred-gate",
            ],
        }

    @router.post("/task-drafts/prepare", response_model=PreparedTaskDraft)
    def prepare_task_draft(payload: TaskDraftPrepareRequest) -> PreparedTaskDraft:
        agent = _assistant(payload.assistant_id)
        allowed_tools = list(agent.get("approved_tools", [])) if agent else []
        stable = "|".join([payload.workspace_id, payload.assistant_id, payload.title, payload.objective])
        draft_id = "draft_" + sha256(stable.encode("utf-8")).hexdigest()[:16]
        return PreparedTaskDraft(
            draft_id=draft_id,
            state="prepared_for_human_review",
            assistant_id=payload.assistant_id,
            workspace_id=payload.workspace_id,
            title=payload.title,
            objective=payload.objective,
            priority=payload.priority,
            allowed_tools=allowed_tools,
            blocked_actions=[
                "shell",
                "git",
                "code_execution",
                "model_execution",
                "pilot_execution",
                "external_web_search",
                "database_write",
                "platform_mutation",
                "agent_self_apply",
            ],
            review_required=True,
            persistence="none",
            execution_authority="none",
            created_at=_now(),
            next_step_ar="راجع المسودة في الشاشة. لا يوجد تنفيذ فعلي أو حفظ خادمي في هذه المرحلة.",
        )

    @router.get("/deferred-gate")
    def deferred_gate() -> dict[str, Any]:
        return {
            "result": "PASS",
            "gate": "DEFERRED_AND_BLOCKED_TOOLS_REASSESSMENT_GATE_V1",
            "current_decision": "PROJECT_READER_ACCEPTED_BACKEND_ALIGNMENT_IN_PROGRESS",
            "promoted_now": ["backend_frontend_alignment_contracts", "task_draft_prepare_endpoint", "tool_registry_metadata"],
            "still_deferred": DEFERRED_TOOLS,
            "still_blocked": BLOCKED_TOOLS,
            "reassessment_rule_ar": "لا تدخل أي أداة مؤجلة أو مرفوضة قبل تفويض مستقل وبوابة سلامة واضحة.",
        }

    @router.get("/boundary")
    def boundary() -> dict[str, Any]:
        return {
            "result": "PASS",
            "boundary": {
                "source_mutation_by_runtime": "none",
                "database_write": "none",
                "model_execution": "blocked",
                "pilot_execution": "not_executed",
                "shell": "blocked",
                "git": "blocked",
                "web_search": "blocked",
                "platform_mutation": "blocked",
            },
        }

    return router
