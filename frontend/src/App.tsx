import { useEffect, useMemo, useState } from "react";
import { readJson } from "./api/client";
import { asItems, asRecord, count, itemLabel, itemSubtitle, text, uppercaseStatus } from "./api/presentation";
import type { CollectionResponse, ReadState, UnknownRecord } from "./api/types";
import { Layout } from "./components/Layout";
import { Icon, type IconName } from "./components/Icon";
import { BlockedAction, BoundaryPanel, MetricCard, SectionHeading, StateGate } from "./components/OperationalPanels";

const DEFAULT_WORKSPACE = "palwakf_government";

type AgentGroup = "operational" | "engineering" | "governance" | "local_ai";

type CatalogAgent = {
  id: string;
  name: string;
  group: AgentGroup;
  groupLabel: string;
  icon: IconName;
  purpose: string;
  useCase: string;
  output: string;
  authority: string;
  state: string;
  examples: string[];
};


type ToolStatus = "approved" | "deferred" | "blocked";

type ToolDefinition = {
  id: string;
  name: string;
  status: ToolStatus;
  category: string;
  purpose: string;
  boundary: string;
  output: string;
};

type TaskDraftStatus = "draft" | "ready_for_review" | "accepted_as_plan" | "returned";

type TaskDraft = {
  id: string;
  title: string;
  description: string;
  agentId: string;
  agentName: string;
  agentGroup: string;
  workspaceId: string;
  status: TaskDraftStatus;
  authority: "PREPARE_ONLY_NO_EXECUTION";
  tools: string[];
  blockedActions: string[];
  createdAt: string;
  source: "backend_prepare" | "browser_fallback";
  backendDraftId?: string;
  backendState?: string;
  backendPersistence?: string;
  backendPreparedAt?: string;
  backendError?: string;
  reviewNote?: string;
  reviewUpdatedAt?: string;
};

type BackendPreparedTaskDraft = {
  draft_id?: string;
  state?: string;
  assistant_id?: string;
  workspace_id?: string;
  title?: string;
  objective?: string;
  priority?: string;
  allowed_tools?: string[];
  blocked_actions?: string[];
  review_required?: boolean;
  persistence?: string;
  execution_authority?: string;
  created_at?: string;
  next_step_ar?: string;
};

type DraftPreparationOutcome = {
  draft: TaskDraft;
  mode: "backend_prepare" | "browser_fallback";
  message: string;
};

const TASK_DRAFT_STORAGE_KEY = "palwakf.localAgents.taskDrafts.v1";

const CATALOG_GROUPS: { id: "all" | AgentGroup; label: string }[] = [
  { id: "all", label: "الكل" },
  { id: "operational", label: "تشغيلي" },
  { id: "engineering", label: "هندسي" },
  { id: "governance", label: "حوكمة" },
  { id: "local_ai", label: "ذكاء محلي" },
];

const ASSISTANT_CATALOG: CatalogAgent[] = [
  { id: "coordinator", name: "المساعد المنسّق العام", group: "operational", groupLabel: "تشغيلي", icon: "agent", purpose: "يفهم الطلب، يختار المساعد المناسب، ويقسم العمل إلى خطوات قابلة للمراجعة.", useCase: "عندما يكون الطلب عامًا أو متعدد المراحل وتريد معرفة من يبدأ وماذا بعد.", output: "خطة عمل، تصنيف المهمة، وتسلسل مساعدين مقترح.", authority: "اقتراح فقط — لا يطبق ولا يكتب.", state: "READY_FOR_TASK_DRAFT", examples: ["رتب دفعة تطوير الشاشة", "اختر المساعدين المناسبين لهذه المشكلة"] },
  { id: "task_analyst", name: "مساعد تحليل المهام", group: "operational", groupLabel: "تشغيلي", icon: "task", purpose: "يحوّل الطلب الخام إلى مهمة منظمة لها نطاق ومخرجات ومعايير قبول.", useCase: "عند وجود فكرة عامة تحتاج صياغة تنفيذية مضبوطة قبل التطوير.", output: "Task brief، نطاق، مخاطر، ومعايير قبول.", authority: "تحضير فقط — لا يرسل أوامر تشغيل.", state: "READY_FOR_TASK_DRAFT", examples: ["حوّل هذا الطلب إلى مهمة", "اكتب معايير قبول للواجهة"] },
  { id: "error_triage_agent", name: "مساعد إصلاح الأخطاء", group: "operational", groupLabel: "تشغيلي", icon: "pulse", purpose: "يشخص الخطأ بسرعة ويحدد هل نعيد التشغيل أم نتوقف ونقرأ الأدلة.", useCase: "عند ظهور خطأ PowerShell أو build أو route أو server unreachable.", output: "Root cause، خطوة إصلاح واحدة، وما لا يجب تشغيله.", authority: "تشخيص فقط — لا Rollback ولا Apply.", state: "READY_FOR_TASK_DRAFT", examples: ["حلل خطأ npm.ps1", "لماذا عاد ExitCode=1؟"] },
  { id: "project_reader", name: "مساعد قراءة المشروع", group: "engineering", groupLabel: "هندسي", icon: "project", purpose: "يرسم خريطة الملفات والمسارات دون تغيير أي ملف.", useCase: "قبل أي تعديل لمعرفة أين App وRouter وComponents وDist.", output: "خريطة مشروع، ملفات مؤثرة، ومسارات آمنة.", authority: "Read-only — قراءة فقط.", state: "READ_ONLY_READY", examples: ["اعرض ملفات الواجهة", "ما المسارات المتاحة؟"] },
  { id: "frontend_designer", name: "مساعد الواجهة الأمامية", group: "engineering", groupLabel: "هندسي", icon: "tool", purpose: "يبني شاشة المساعدين، البطاقات، المهام، وتجربة RTL العربية.", useCase: "عند تعديل لوحة البداية أو صفحة المساعدين أو محرر المهمة.", output: "تصميم واجهة، مكونات React، وتحسينات CSS مقترحة.", authority: "Proposal-only — لا يطبق بلا تفويض.", state: "READY_FOR_UI_TASK", examples: ["حسن صفحة المساعدين", "أضف بطاقة مساعد جديدة"] },
  { id: "backend_reader", name: "مساعد قراءة Backend/API", group: "engineering", groupLabel: "هندسي", icon: "workspace", purpose: "يميز بين UI routes وAPI routes حتى لا نفحص مسارات خاطئة.", useCase: "قبل UAT أو إضافة رابط صفحة جديدة.", output: "Route matrix، endpoints، وحدود GET-only.", authority: "Read-only — لا يغير Backend.", state: "READ_ONLY_READY", examples: ["ما API المتاح؟", "هل /agent-console/agents موجود؟"] },
  { id: "uat_tester", name: "مساعد الفحص والاختبار", group: "engineering", groupLabel: "هندسي", icon: "review", purpose: "يفحص الشاشة والبناء والروابط بفحوص قصيرة ومباشرة.", useCase: "بعد أي تعديل واجهة للتأكد من PASS/FAIL دون تعقيد زائد.", output: "قائمة فحص، نتيجة PASS/FAIL، وسبب الفشل إن وجد.", authority: "فحص فقط — لا يعدل.", state: "READY_FOR_UAT", examples: ["افحص الشاشة بصريًا", "تحقق من مسارات agent-console"] },
  { id: "ux_reviewer", name: "مساعد تجربة المستخدم", group: "engineering", groupLabel: "هندسي", icon: "home", purpose: "يراجع هل الشاشة مفهومة كمنتج لا كلوحة حوكمة.", useCase: "عند الشعور أن الشاشة جميلة لكنها غير عملية أو مزدحمة.", output: "ملاحظات UX، ترتيب أولويات، ونصوص أوضح.", authority: "مراجعة فقط — لا يطبق.", state: "READY_FOR_REVIEW", examples: ["هل الصفحة مفهومة؟", "اجعل مسار المهمة أوضح"] },
  { id: "safety_governor", name: "مساعد السلامة والحوكمة", group: "governance", groupLabel: "حوكمة", icon: "shield", purpose: "يراقب حدود عدم التنفيذ: لا Shell، لا Git، لا DB، لا Model، لا Network.", useCase: "قبل فتح أي صلاحية أو ربط نموذج أو تنفيذ Apply.", output: "Boundary statement، مخاطر، وما هو مسموح أو محجوب.", authority: "حارس حدود — لا ينفذ.", state: "GUARDRAIL_ACTIVE", examples: ["هل هذا الإجراء آمن؟", "ما المخاطر قبل التفويض؟"] },
  { id: "evidence_baseline_keeper", name: "مساعد الأدلة والـBaseline", group: "governance", groupLabel: "حوكمة", icon: "evidence", purpose: "يلخص الأدلة ويرتب Baseline بعد قبول الشاشة أو الدفعة.", useCase: "في نهاية الدفعة فقط، وليس في بداية التطوير اليومي.", output: "Evidence summary، baseline candidate، وملف توريث.", authority: "توثيق وترقية مقترحة — لا يكرر Promotion بلا تفويض.", state: "USE_AFTER_ACCEPTANCE", examples: ["جهز ملف توريث", "لخص أدلة القبول"] },
  { id: "documentation_handoff", name: "مساعد التوثيق والتوريث", group: "governance", groupLabel: "حوكمة", icon: "evidence", purpose: "ينتج ملف استئناف للجلسة القادمة بنقطة توقف واضحة.", useCase: "عند إغلاق جلسة أو دفعة وتريد ألا نبدأ من الصفر.", output: "ما تم، ما لم يتم، الملفات المعدلة، ونقطة الاستئناف.", authority: "توثيق فقط.", state: "READY_FOR_HANDOFF", examples: ["اكتب توريث شامل", "ثبت نقطة الاستئناف"] },
  { id: "local_model_manager", name: "مساعد إدارة النموذج المحلي", group: "local_ai", groupLabel: "ذكاء محلي", icon: "lock", purpose: "يعرض حالة Ollama والنموذج المحلي وPilot دون تشغيل تلقائي.", useCase: "عند الانتقال لاحقًا من التحضير إلى Pilot مضبوط.", output: "حالة النموذج، جاهزية Pilot، وحدود التنفيذ.", authority: "Model execution disabled حاليًا.", state: "MODEL_OFF", examples: ["هل النموذج جاهز؟", "ما شروط Pilot؟"] },
];

const TOOL_STATUS_LABELS: Record<ToolStatus, string> = {
  approved: "مقبولة الآن",
  deferred: "مؤجلة",
  blocked: "مرفوضة حاليًا",
};

const TOOL_STATUS_DETAIL: Record<ToolStatus, string> = {
  approved: "تدخل في مرحلة Tool Registry + Task Drafting بدون تنفيذ فعلي.",
  deferred: "تحفظ للمراجعة بعد إغلاق المرحلة الأولى بنجاح.",
  blocked: "تبقى خارج النطاق حتى تفويض مستقل وبوابة مخاطر لاحقة.",
};

const LOCAL_TOOL_REGISTRY: ToolDefinition[] = [
  { id: "tool_registry", name: "سجل الأدوات المحلي", status: "approved", category: "حوكمة", purpose: "تعريف الأدوات وتصنيفها وربطها بالمساعدين دون تشغيلها.", boundary: "Metadata only — لا يستدعي أداة خارجية.", output: "قائمة أدوات وحالاتها وحدودها." },
  { id: "task_planner", name: "مخطط المهام", status: "approved", category: "تشغيل", purpose: "تحويل الطلب إلى خطوات ومعايير قبول.", boundary: "تحضير فقط — لا ينفذ الخطوات.", output: "خطة مهمة منظمة." },
  { id: "task_drafter", name: "منشئ مسودة المهمة", status: "approved", category: "تشغيل", purpose: "إنشاء Draft محلي قابل للمراجعة من كتالوج المساعدين.", boundary: "Browser local draft only — لا POST ولا DB.", output: "مسودة مهمة محلية." },
  { id: "project_reader", name: "قارئ المشروع", status: "approved", category: "هندسة", purpose: "قراءة بنية المشروع ومساراته فعليًا عبر GET-only عند التفويض.", boundary: "Read-only داخل workspace فقط، بدون Shell أو Git أو Model.", output: "خريطة ملفات، ملفات رئيسية، ومصفوفة مسارات." },
  { id: "route_api_reader", name: "قارئ Routes/API", status: "approved", category: "هندسة", purpose: "تمييز UI routes عن API endpoints ومنع فحوص خاطئة.", boundary: "GET/read-only فقط.", output: "Route matrix آمنة." },
  { id: "document_reader", name: "قارئ الملفات والمستندات", status: "approved", category: "معرفة", purpose: "تحضير قراءة ملفات محلية لاحقًا بصلاحية قراءة فقط.", boundary: "Read-only، لا تعديل ولا رفع.", output: "ملخص محتوى أو Markdown." },
  { id: "evidence_summarizer", name: "ملخص الأدلة", status: "approved", category: "حوكمة", purpose: "تلخيص أدلة التشغيل دون فتح Promotion جديد تلقائيًا.", boundary: "Summarize only — لا baseline promotion.", output: "ملخص أدلة وحدود." },
  { id: "local_json_store", name: "Local JSON/Browser Draft Store", status: "approved", category: "تخزين محلي", purpose: "حفظ مسودات واجهة أولية محليًا داخل المتصفح أو JSON محكوم لاحقًا.", boundary: "لا DB خارجي ولا منصة.", output: "مسودات قابلة للعرض." },
  { id: "vector_memory", name: "ChromaDB / LanceDB / Qdrant", status: "deferred", category: "ذاكرة", purpose: "ذاكرة دلالية طويلة المدى لاحقًا.", boundary: "مؤجلة حتى تثبيت دورة المهام والمخرجات.", output: "Memory/RAG index لاحق." },
  { id: "langgraph", name: "LangGraph Orchestration", status: "deferred", category: "تنسيق وكلاء", purpose: "تدفق وكلاء متعدد الخطوات لاحقًا.", boundary: "لا orchestration قبل تدقيق Tool Registry.", output: "Agent graph لاحق." },
  { id: "web_search", name: "SearXNG / Web Search", status: "deferred", category: "بحث", purpose: "بحث خارجي أو محلي مستضاف لاحقًا.", boundary: "لا Network في المرحلة الحالية.", output: "نتائج بحث لاحقًا." },
  { id: "ocr", name: "OCR / Tesseract", status: "deferred", category: "وسائط", purpose: "قراءة صور ووثائق ممسوحة لاحقًا.", boundary: "مؤجل حتى مرحلة الوثائق.", output: "نص مستخرج لاحقًا." },
  { id: "whisper", name: "Whisper / STT", status: "deferred", category: "وسائط", purpose: "تفريغ صوت محلي لاحقًا.", boundary: "مؤجل حتى تفعيل مسار صوتي.", output: "تفريغ صوت لاحقًا." },
  { id: "docker_sandbox", name: "Docker Code Sandbox", status: "deferred", category: "تنفيذ آمن", purpose: "تنفيذ أكواد داخل حاوية لاحقًا.", boundary: "مؤجل بسبب المخاطر والتعقيد.", output: "نتائج كود لاحقة." },
  { id: "shell_execution", name: "Shell Execution", status: "blocked", category: "محظور", purpose: "تشغيل أوامر نظام.", boundary: "مرفوض حاليًا.", output: "لا مخرج." },
  { id: "git_operations", name: "Git Operations", status: "blocked", category: "محظور", purpose: "Pull/commit/push أو فروع.", boundary: "مرفوض حاليًا.", output: "لا مخرج." },
  { id: "code_execution", name: "Code Interpreter فعلي", status: "blocked", category: "محظور", purpose: "تشغيل كود يولده المساعد.", boundary: "مرفوض حتى Sandbox مضبوط.", output: "لا مخرج." },
  { id: "model_execution", name: "Model / Pilot Execution", status: "blocked", category: "محظور", purpose: "تشغيل نموذج أو Pilot.", boundary: "مرفوض حتى تفويض مستقل.", output: "لا مخرج." },
  { id: "platform_mutation", name: "Platform Mutation", status: "blocked", category: "محظور", purpose: "تعديل منصة أو قاعدة خارجية.", boundary: "مرفوض.", output: "لا مخرج." },
];

const ASSISTANT_TOOL_MAP: Record<string, string[]> = {
  coordinator: ["tool_registry", "task_planner", "task_drafter", "evidence_summarizer"],
  task_analyst: ["tool_registry", "task_planner", "task_drafter"],
  error_triage_agent: ["tool_registry", "route_api_reader", "evidence_summarizer"],
  project_reader: ["tool_registry", "project_reader", "route_api_reader"],
  frontend_designer: ["tool_registry", "task_planner", "project_reader"],
  backend_reader: ["tool_registry", "route_api_reader", "project_reader"],
  uat_tester: ["tool_registry", "route_api_reader", "evidence_summarizer"],
  ux_reviewer: ["tool_registry", "task_planner", "task_drafter"],
  safety_governor: ["tool_registry", "evidence_summarizer"],
  evidence_baseline_keeper: ["tool_registry", "evidence_summarizer"],
  documentation_handoff: ["tool_registry", "evidence_summarizer", "document_reader"],
  local_model_manager: ["tool_registry"],
};

const BLOCKED_ACTIONS = ["Shell", "Git", "Code execution", "Model execution", "Pilot", "External web", "Platform mutation", "Ungoverned DB write"];

type FrontendBatchItem = {
  id: string;
  title: string;
  status: "accepted" | "built" | "blocked" | "backend";
  area: string;
  summary: string;
};

type BackendProcedureItem = {
  id: string;
  title: string;
  priority: "P0" | "P1" | "P2";
  status: "required" | "later" | "blocked";
  endpoint: string;
  summary: string;
  guardrail: string;
};

const FRONTEND_MEGA_BATCH_ITEMS: FrontendBatchItem[] = [
  { id: "catalog", title: "كتالوج المساعدين", status: "accepted", area: "Tools", summary: "بطاقات المساعدين، الفلاتر، اختيار المساعد، وبداية المسودة." },
  { id: "tool_registry", title: "سجل الأدوات", status: "accepted", area: "Tools", summary: "تصنيف الأدوات إلى مقبولة ومؤجلة ومرفوضة مع حدود كل أداة." },
  { id: "task_drafting", title: "مسودات المهام", status: "accepted", area: "Tasks", summary: "إنشاء مسودة محلية داخل المتصفح وعرضها في صفحة المهام." },
  { id: "project_reader", title: "قارئ المشروع", status: "accepted", area: "Projects", summary: "قراءة metadata وroute matrix من Backend read-only." },
  { id: "task_lifecycle", title: "لوحة دورة المهمة", status: "built", area: "Tasks", summary: "عرض مراحل المسودة: صياغة، مراجعة، أدوات، قرار، دون تنفيذ." },
  { id: "backend_alignment", title: "مطابقة الفرونت والباك إند", status: "backend", area: "Diagnostics", summary: "دليل إجراءات Backend موازٍ حتى لا تتوسع الواجهة بلا عقود خادمية." },
  { id: "future_tools_gate", title: "بوابة المؤجل والمرفوض", status: "built", area: "Tools", summary: "إظهار ما سيعاد تقييمه لاحقًا دون إدخاله في هذه المرحلة." },
  { id: "execution_wall", title: "جدار منع التنفيذ", status: "blocked", area: "Pilot", summary: "Shell/Git/Model/Pilot/Code execution تبقى مقفلة بصريًا ووظيفيًا." },
];

const BACKEND_ALIGNMENT_ACTIONS: BackendProcedureItem[] = [
  { id: "task_draft_api", title: "Task Draft API", priority: "P0", status: "required", endpoint: "GET/POST لاحقًا: /api/v1/task-drafts", summary: "تحويل مسودات localStorage إلى مسودات خادمية محكومة عند التفويض فقط.", guardrail: "prepare-only، actor-scoped، no execution dispatch." },
  { id: "tool_registry_api", title: "Tool Registry API", priority: "P0", status: "required", endpoint: "GET: /api/v1/tools/registry", summary: "نقل سجل الأدوات من ثابت Frontend إلى عقد Backend قابل للتدقيق.", guardrail: "metadata only، لا invoke tool." },
  { id: "assistant_tool_map_api", title: "Assistant-to-tool Mapping API", priority: "P0", status: "required", endpoint: "GET: /api/v1/assistants/tool-map", summary: "ربط المساعدين بالأدوات المسموحة من مصدر خادمي موحد.", guardrail: "approved/deferred/blocked only." },
  { id: "project_reader_deepen", title: "Project Reader Detail Contract", priority: "P1", status: "required", endpoint: "GET: /api/v1/project-reader/...", summary: "إضافة endpoints تفصيلية للملفات المختارة مع حجب الأسرار والمسارات غير المسموحة.", guardrail: "workspace-scoped allowlist، no content outside roots." },
  { id: "review_gate_api", title: "Task Review Gate API", priority: "P1", status: "later", endpoint: "POST لاحقًا: /api/v1/task-drafts/{id}/review", summary: "تحويل المسودة إلى مراجعة بشرية محكومة.", guardrail: "review is not execution." },
  { id: "document_reader", title: "Document Reader API", priority: "P2", status: "later", endpoint: "GET لاحقًا: /api/v1/document-reader", summary: "قراءة مستندات محلية داخل workspace فقط.", guardrail: "read-only، size limits، no OCR initially." },
  { id: "blocked_runtime", title: "Execution Runtime APIs", priority: "P2", status: "blocked", endpoint: "Shell/Git/Model/Pilot", summary: "تبقى خارج النطاق في هذه الدفعة.", guardrail: "requires separate gate after reassessment." },
];

function batchTone(status: FrontendBatchItem["status"]): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "accepted") return "green";
  if (status === "built") return "blue";
  if (status === "backend") return "gold";
  return "red";
}

function backendTone(status: BackendProcedureItem["status"]): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "required") return "gold";
  if (status === "later") return "blue";
  return "red";
}


function useRead<T>(path: string): ReadState<T> {
  const [state, setState] = useState<ReadState<T>>({ kind: "loading" });
  useEffect(() => {
    let active = true;
    void readJson<T>(path).then((result) => { if (active) setState(result); });
    return () => { active = false; };
  }, [path]);
  return state;
}

function safeStatus(value: unknown, fallback = "READ ONLY"): string {
  return uppercaseStatus(value, fallback);
}

function recordDetail(item: UnknownRecord, keys: string[]): string {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "لا توجد تفاصيل منشورة ضمن نموذج القراءة الآمن.";
}

function firstText(item: UnknownRecord, keys: string[], fallback = "غير متاح"): string {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return fallback;
}

function recordArray(value: unknown): UnknownRecord[] {
  return Array.isArray(value) ? value.filter((item): item is UnknownRecord => typeof item === "object" && item !== null) : [];
}

function displayNumber(value: unknown): string {
  return typeof value === "number" ? value.toLocaleString("ar") : "0";
}


function getAgentById(agentId: string): CatalogAgent {
  return ASSISTANT_CATALOG.find((agent) => agent.id === agentId) ?? ASSISTANT_CATALOG[0];
}

function getToolById(toolId: string): ToolDefinition | undefined {
  return LOCAL_TOOL_REGISTRY.find((tool) => tool.id === toolId);
}

function getAgentTools(agentId: string, status?: ToolStatus): ToolDefinition[] {
  const ids = ASSISTANT_TOOL_MAP[agentId] ?? ["tool_registry", "task_planner"];
  return ids.map(getToolById).filter((tool): tool is ToolDefinition => Boolean(tool)).filter((tool) => status ? tool.status === status : true);
}

function statusTone(status: ToolStatus): "green" | "gold" | "red" | "slate" {
  if (status === "approved") return "green";
  if (status === "deferred") return "gold";
  return "red";
}

function safeLoadDrafts(): TaskDraft[] {
  try {
    const raw = window.localStorage.getItem(TASK_DRAFT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is TaskDraft => typeof item?.id === "string" && typeof item?.title === "string");
  } catch {
    return [];
  }
}

function safeStoreDrafts(drafts: TaskDraft[]) {
  try {
    window.localStorage.setItem(TASK_DRAFT_STORAGE_KEY, JSON.stringify(drafts.slice(0, 30)));
  } catch {
    // Browser-only draft persistence can be unavailable. The UI remains prepare-only.
  }
}

function createDraft(agent: CatalogAgent, title: string, description: string, overrides: Partial<TaskDraft> = {}): TaskDraft {
  const now = new Date();
  return {
    id: overrides.id ?? `draft-${now.getTime()}-${agent.id}`,
    title: title.trim() || `مهمة جديدة — ${agent.name}`,
    description: description.trim() || agent.examples[0],
    agentId: overrides.agentId ?? agent.id,
    agentName: overrides.agentName ?? agent.name,
    agentGroup: overrides.agentGroup ?? agent.groupLabel,
    workspaceId: overrides.workspaceId ?? DEFAULT_WORKSPACE,
    status: overrides.status ?? "draft",
    authority: "PREPARE_ONLY_NO_EXECUTION",
    tools: overrides.tools ?? getAgentTools(agent.id, "approved").map((tool) => tool.id),
    blockedActions: overrides.blockedActions ?? BLOCKED_ACTIONS,
    createdAt: overrides.createdAt ?? now.toISOString(),
    source: overrides.source ?? "browser_fallback",
    backendDraftId: overrides.backendDraftId,
    backendState: overrides.backendState,
    backendPersistence: overrides.backendPersistence,
    backendPreparedAt: overrides.backendPreparedAt,
    backendError: overrides.backendError,
    reviewNote: overrides.reviewNote,
    reviewUpdatedAt: overrides.reviewUpdatedAt,
  };
}


const TASK_DRAFT_STATUS_LABELS: Record<TaskDraftStatus, string> = {
  draft: "مسودة",
  ready_for_review: "جاهزة للمراجعة",
  accepted_as_plan: "مقبولة كخطة",
  returned: "معادة للصياغة",
};

const TASK_DRAFT_STATUS_DETAILS: Record<TaskDraftStatus, string> = {
  draft: "قيد الصياغة. لا تنفيذ ولا حفظ دائم.",
  ready_for_review: "جاهزة لمراجعة بشرية prepare-only.",
  accepted_as_plan: "مقبولة كخطة عمل فقط، وليست تفويض تنفيذ.",
  returned: "معادة لتحسين الصياغة أو النطاق.",
};

function taskDraftStatusTone(status: TaskDraftStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "accepted_as_plan") return "green";
  if (status === "ready_for_review") return "blue";
  if (status === "returned") return "gold";
  return "slate";
}

function backendErrorText(value: unknown): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (value && typeof value === "object" && "detail" in value) {
    const detail = (value as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    try { return JSON.stringify(detail); } catch { return "BACKEND_DETAIL_UNREADABLE"; }
  }
  return "BACKEND_PREPARE_UNAVAILABLE";
}

async function prepareDraftWithBackend(agent: CatalogAgent, title: string, description: string): Promise<DraftPreparationOutcome> {
  const fallback = (reason: string): DraftPreparationOutcome => ({
    draft: createDraft(agent, title, description, { source: "browser_fallback", backendError: reason }),
    mode: "browser_fallback",
    message: `تعذر التحضير عبر Backend؛ تم إنشاء مسودة متصفح فقط: ${reason}`,
  });
  try {
    const response = await fetch("/api/v1/backend-frontend-alignment/task-drafts/prepare", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json; charset=utf-8" },
      credentials: "omit",
      body: JSON.stringify({
        assistant_id: agent.id,
        workspace_id: DEFAULT_WORKSPACE,
        title: title.trim() || `مهمة جديدة — ${agent.name}`,
        objective: description.trim() || agent.examples[0],
        priority: "normal",
      }),
    });
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) return fallback(backendErrorText(body));
    const prepared = (body ?? {}) as BackendPreparedTaskDraft;
    const backendId = typeof prepared.draft_id === "string" && prepared.draft_id.trim() ? prepared.draft_id.trim() : `backend-draft-${Date.now()}-${agent.id}`;
    const preparedTitle = typeof prepared.title === "string" ? prepared.title : title;
    const preparedObjective = typeof prepared.objective === "string" ? prepared.objective : description;
    const createdAt = typeof prepared.created_at === "string" ? prepared.created_at : new Date().toISOString();
    return {
      draft: createDraft(agent, preparedTitle, preparedObjective, {
        id: backendId,
        workspaceId: typeof prepared.workspace_id === "string" ? prepared.workspace_id : DEFAULT_WORKSPACE,
        tools: Array.isArray(prepared.allowed_tools) ? prepared.allowed_tools : getAgentTools(agent.id, "approved").map((tool) => tool.id),
        blockedActions: Array.isArray(prepared.blocked_actions) ? prepared.blocked_actions : BLOCKED_ACTIONS,
        createdAt,
        source: "backend_prepare",
        backendDraftId: backendId,
        backendState: typeof prepared.state === "string" ? prepared.state : "prepared_for_human_review",
        backendPersistence: typeof prepared.persistence === "string" ? prepared.persistence : "none",
        backendPreparedAt: createdAt,
      }),
      mode: "backend_prepare",
      message: `تم تحضير مسودة عبر Backend: ${backendId}`
    };
  } catch (error) {
    return fallback(error instanceof Error ? error.message : "NETWORK_OR_BACKEND_ERROR");
  }
}

function useTaskDrafts() {
  const [drafts, setDrafts] = useState<TaskDraft[]>(() => safeLoadDrafts());
  const addDraft = (draft: TaskDraft) => {
    setDrafts((current) => {
      const next = [draft, ...current].slice(0, 30);
      safeStoreDrafts(next);
      return next;
    });
  };
  const transitionDraft = (draftId: string, status: TaskDraftStatus, reviewNote?: string) => {
    setDrafts((current) => {
      const next = current.map((draft) => draft.id === draftId ? {
        ...draft,
        status,
        reviewNote: reviewNote ?? TASK_DRAFT_STATUS_DETAILS[status],
        reviewUpdatedAt: new Date().toISOString(),
      } : draft);
      safeStoreDrafts(next);
      return next;
    });
  };
  const clearDrafts = () => {
    setDrafts([]);
    safeStoreDrafts([]);
  };
  return { drafts, addDraft, transitionDraft, clearDrafts };
}

function Badge({ children, tone = "slate" }: { children: string; tone?: "slate" | "blue" | "gold" | "red" | "green" }) {
  return <span className={`mini-badge mini-badge-${tone}`}>{children}</span>;
}

function DisabledButton({ children, icon = "lock" }: { children: string; icon?: IconName }) {
  return <button className="disabled-action" type="button" disabled><Icon name={icon} size={15}/>{children}</button>;
}

function CollectionReadPanel({ data, empty, label, detailKeys, statusKey = "status", icon = "evidence" }: { data: CollectionResponse; empty: string; label: string; detailKeys: string[]; statusKey?: string; icon?: IconName }) {
  const items = asItems(data);
  return <div className="agent-grid" aria-label={label}>
    {items.map((item, index) => <article className="agent-card" key={`${itemLabel(item, index)}-${index}`}>
      <span className="agent-avatar"><Icon name={icon} size={20}/></span>
      <div><strong>{itemLabel(item, index)}</strong><p>{recordDetail(item, detailKeys)}</p></div>
      <span className="status-chip">{safeStatus(item[statusKey])}</span>
    </article>)}
    {items.length === 0 && <article className="empty-card">{empty}</article>}
  </div>;
}

function StartHerePanel() {
  return <section className="start-panel" aria-label="ابدأ من هنا">
    <div className="start-card primary"><span>01</span><h3>اختر مساعدًا</h3><p>راجع الدور المناسب: محلل، مصمم، مطور، مراجع سيادة، أو موثق.</p><a href="/agent-console/tools">عرض المساعدين</a></div>
    <div className="start-card"><span>02</span><h3>صغ المهمة</h3><p>اكتب المطلوب داخل نموذج تحضير مرئي. الحفظ والتنفيذ مقفلان حاليًا.</p><a href="/agent-console/tasks">فتح المهام</a></div>
    <div className="start-card"><span>03</span><h3>راجع المخرج</h3><p>أي مخرج لاحق يبقى Proposal فقط، ولا يصبح تنفيذًا أو تطبيقًا.</p><a href="/agent-console/reviews">المراجعات</a></div>
  </section>;
}

function TaskComposerMock({ agent = ASSISTANT_CATALOG[0], onCreateDraft, onPrepareDraft }: { agent?: CatalogAgent; onCreateDraft?: (draft: TaskDraft) => void; onPrepareDraft?: (agent: CatalogAgent, title: string, description: string) => Promise<void> | void }) {
  const canDraft = typeof onCreateDraft === "function" || typeof onPrepareDraft === "function";
  const backendBound = typeof onPrepareDraft === "function";
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState(`مهمة جديدة — ${agent.name}`);
  const [description, setDescription] = useState(agent.examples[0]);
  const approvedTools = getAgentTools(agent.id, "approved");

  useEffect(() => {
    setTitle(`مهمة جديدة — ${agent.name}`);
    setDescription(agent.examples[0]);
  }, [agent.id, agent.name, agent.examples]);

  const handleCreate = async () => {
    if (!canDraft || busy) return;
    if (onPrepareDraft) {
      setBusy(true);
      try {
        await onPrepareDraft(agent, title, description);
      } finally {
        setBusy(false);
      }
      return;
    }
    if (onCreateDraft) onCreateDraft(createDraft(agent, title, description));
  };

  return <article className="composer-card" aria-label="محرر مسودة مهمة محلية">
    <div className="composer-head"><div><p>محرر مسودة مهمة</p><h2>إنشاء مسودة — {agent.name}</h2><span>{canDraft ? (backendBound ? "يرتبط بعقد Backend prepare: POST محكوم، لا حفظ خادمي، لا تنفيذ." : "يحفظ محليًا داخل المتصفح فقط. لا Backend، لا تنفيذ.") : "نموذج عرض. افتح كتالوج المساعدين لإنشاء مسودة."}</span></div><Badge tone={canDraft ? "green" : "red"}>{backendBound ? "Backend prepare" : canDraft ? "Draft enabled" : "مقفل"}</Badge></div>
    <div className="form-grid">
      <label>نوع المهمة<input value={`${agent.groupLabel} / ${agent.state}`} disabled readOnly /></label>
      <label>المساعد المختار<input value={`${agent.name} — ${agent.id}`} disabled readOnly /></label>
      <label className="wide">عنوان المسودة<input value={title} onChange={(event) => setTitle(event.target.value)} disabled={!canDraft} /></label>
      <label className="wide">وصف المهمة<textarea value={description} onChange={(event) => setDescription(event.target.value)} disabled={!canDraft} /></label>
    </div>
    <div className="draft-tool-strip" aria-label="الأدوات المسموحة لهذه المسودة">
      {approvedTools.map((tool) => <span key={tool.id}><Icon name="tool" size={14}/>{tool.name}</span>)}
      {approvedTools.length === 0 && <span><Icon name="lock" size={14}/> لا توجد أدوات مفعلة لهذا المساعد</span>}
    </div>
    <div className="composer-actions">
      {canDraft ? <button className="primary-action" type="button" onClick={handleCreate} disabled={busy}><Icon name="task" size={15}/> {busy ? "جار التحضير..." : backendBound ? "تحضير مسودة عبر Backend" : "حفظ مسودة محلية"}</button> : <DisabledButton icon="task">حفظ كمسودة — غير مفعل هنا</DisabledButton>}
      <DisabledButton icon="agent">تحضير بواسطة نموذج — محجوب</DisabledButton>
    </div>
  </article>;
}

function CatalogAgentCard({ agent, selected, onSelect }: { agent: CatalogAgent; selected?: boolean; onSelect?: (agent: CatalogAgent) => void }) {
  return <article className={`agent-card rich catalog-card ${selected ? "catalog-card-selected" : ""}`}>
    <span className="agent-avatar"><Icon name={agent.icon} size={21}/></span>
    <div className="agent-copy"><strong>{agent.name}</strong><p>{agent.purpose}</p></div>
    <div className="agent-meta"><Badge tone="blue">{agent.groupLabel}</Badge><Badge tone="gold">{agent.state}</Badge><Badge tone="slate">Proposal-only</Badge></div>
    <div className="tool-chip-row">{getAgentTools(agent.id, "approved").slice(0, 3).map((tool) => <span key={tool.id}>{tool.name}</span>)}</div>
    <div className="use-case"><b>متى أستخدمه؟</b><span>{agent.useCase}</span></div>
    <div className="use-case"><b>ما الذي ينتجه؟</b><span>{agent.output}</span></div>
    <div className="catalog-examples"><b>أمثلة</b>{agent.examples.map((example) => <span key={example}>{example}</span>)}</div>
    {onSelect ? <button className="catalog-start-button" type="button" onClick={() => onSelect(agent)}><Icon name="task" size={15}/> أنشئ مهمة لهذا المساعد</button> : <a className="catalog-start-link" href="/agent-console/tools"><Icon name="arrow" size={15}/> عرض التفاصيل</a>}
  </article>;
}

function AgentShowcase({ limit }: { data?: CollectionResponse; limit?: number }) {
  const visible = typeof limit === "number" ? ASSISTANT_CATALOG.slice(0, limit) : ASSISTANT_CATALOG;
  return <div className="agent-grid agent-grid-rich">
    {visible.map((agent) => <CatalogAgentCard key={agent.id} agent={agent}/>) }
  </div>;
}

function AssistantCatalogConsole() {
  const [group, setGroup] = useState<"all" | AgentGroup>("all");
  const [selected, setSelected] = useState<CatalogAgent>(ASSISTANT_CATALOG[0]);
  const [notice, setNotice] = useState<string>("");
  const draftStore = useTaskDrafts();
  const visible = group === "all" ? ASSISTANT_CATALOG : ASSISTANT_CATALOG.filter((agent) => agent.group === group);
  const handleDraft = async (agent: CatalogAgent, title: string, description: string) => {
    const outcome = await prepareDraftWithBackend(agent, title, description);
    draftStore.addDraft(outcome.draft);
    setNotice(outcome.message);
  };
  return <>
    <section className="catalog-toolbar" aria-label="فلترة المساعدين">
      <div><p>كتالوج المساعدين</p><strong>{visible.length} مساعدًا ظاهرًا</strong><span>اختيار المساعد يملأ مسودة مهمة محلية. لا يوجد تنفيذ فعلي.</span></div>
      <div className="catalog-tabs">{CATALOG_GROUPS.map((item) => <button key={item.id} type="button" className={group === item.id ? "active" : ""} onClick={() => setGroup(item.id)}>{item.label}</button>)}</div>
    </section>
    {notice && <section className="local-draft-notice"><Icon name="task" size={18}/><div><strong>{notice}</strong><span>تظهر المسودة في صفحة المهام. Backend prepare لا يحفظ خادميًا؛ localStorage يبقى للعرض فقط.</span></div><a href="/agent-console/tasks#local-drafts">عرض المسودات</a></section>}
    <section className="content-grid primary-grid catalog-task-grid">
      <TaskComposerMock agent={selected} onPrepareDraft={handleDraft}/>
      <article className="selected-agent-panel">
        <SectionHeading eyebrow="المساعد المختار" title={selected.name} detail={selected.purpose}/>
        <div className="selected-agent-facts">
          <div><span>النوع</span><b>{selected.groupLabel}</b></div>
          <div><span>الحالة</span><b>{selected.state}</b></div>
          <div><span>المسودات المحلية</span><b>{draftStore.drafts.length}</b></div>
        </div>
        <div className="use-case"><b>الأدوات المسموحة</b><span>{getAgentTools(selected.id, "approved").map((tool) => tool.name).join("، ") || "لا توجد أدوات مفعلة."}</span></div>
        <BlockedAction icon="lock" title="لا يوجد تنفيذ" detail="تحضير Backend يعيد Envelope فقط: draft_id، أدوات مسموحة، وexecution_authority=none. لا حفظ دائم ولا تشغيل."/>
      </article>
    </section>
    <div className="agent-grid agent-grid-rich catalog-grid">
      {visible.map((agent) => <CatalogAgentCard key={agent.id} agent={agent} selected={selected.id === agent.id} onSelect={setSelected}/>) }
    </div>
  </>;
}


function FrontendMegaOverviewPanel() {
  const accepted = FRONTEND_MEGA_BATCH_ITEMS.filter((item) => item.status === "accepted").length;
  const built = FRONTEND_MEGA_BATCH_ITEMS.filter((item) => item.status === "built").length;
  const backend = FRONTEND_MEGA_BATCH_ITEMS.filter((item) => item.status === "backend").length;
  return <section className="section-block mega-overview-block">
    <SectionHeading eyebrow="Frontend Mega Batch" title="دفعة واجهة أمامية موحدة" detail="تجميع دفعات الفرونت إند المقبولة والمتبقية في إطار واحد، مع فصل واضح لما يحتاج Backend لاحقًا." />
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="review" label="مقبول بصريًا" value={accepted} detail="كتالوج، أدوات، مسودات، قارئ مشروع" tone="gold"/>
      <MetricCard icon="agent" label="بني في هذه الدفعة" value={built} detail="لوحات دورة المهمة والبوابة اللاحقة" tone="blue"/>
      <MetricCard icon="project" label="ينتظر Backend" value={backend} detail="لا فجوة بلا دليل إجراءات" tone="slate"/>
      <MetricCard icon="lock" label="تنفيذ فعلي" value="0" detail="Shell/Git/Model/Pilot محجوبة" tone="red"/>
    </div>
    <div className="mega-batch-grid">
      {FRONTEND_MEGA_BATCH_ITEMS.map((item) => <article className={`mega-batch-card mega-${item.status}`} key={item.id}>
        <div><Badge tone={batchTone(item.status)}>{item.status}</Badge><strong>{item.title}</strong></div>
        <p>{item.summary}</p>
        <small>{item.area}</small>
      </article>)}
    </div>
  </section>;
}

function TaskLifecyclePanel() {
  const steps = [
    ["01", "اختيار المساعد", "من كتالوج المساعدين مع أدواته المقبولة فقط."],
    ["02", "صياغة المسودة", "عنوان، وصف، أدوات مسموحة، ومساحة عمل."],
    ["03", "مراجعة بشرية", "المسودة ليست تنفيذًا ولا تفويضًا."],
    ["04", "Backend لاحق", "تحويلها إلى سجل خادمي يحتاج Task Draft API."],
  ];
  return <section className="section-block">
    <SectionHeading eyebrow="Task Lifecycle" title="دورة حياة المسودة قبل التنفيذ" detail="هذه اللوحة تجعل مرحلة ما قبل التنفيذ واضحة حتى لا تتحول المسودة إلى أمر تشغيل بالخطأ."/>
    <div className="lifecycle-grid">
      {steps.map(([num, title, detail]) => <article className="lifecycle-card" key={num}><span>{num}</span><strong>{title}</strong><p>{detail}</p></article>)}
    </div>
  </section>;
}

function BackendAlignmentGuidePanel() {
  return <section className="section-block backend-alignment-block">
    <SectionHeading eyebrow="Backend Alignment" title="إجراءات الباك إند المطلوبة لاحقًا" detail="هذا ليس تنفيذ Backend الآن؛ إنه دليل منع الفجوة بين الشاشة والعقود الخادمية."/>
    <div className="backend-action-grid">
      {BACKEND_ALIGNMENT_ACTIONS.map((item) => <article className={`backend-action-card backend-${item.status}`} key={item.id}>
        <div className="backend-action-head"><Badge tone={backendTone(item.status)}>{item.priority}</Badge><Badge tone={backendTone(item.status)}>{item.status}</Badge></div>
        <strong>{item.title}</strong>
        <code>{item.endpoint}</code>
        <p>{item.summary}</p>
        <small>{item.guardrail}</small>
      </article>)}
    </div>
  </section>;
}

function ToolBackendContractPanel() {
  const p0 = BACKEND_ALIGNMENT_ACTIONS.filter((item) => item.priority === "P0");
  return <section className="section-block tool-contract-block">
    <SectionHeading eyebrow="Contract First" title="ما يحتاج عقدًا خادميًا قبل توسيع الأدوات" detail="أي أداة تظهر في الواجهة يجب أن تملك حالة، صلاحية، وحدودًا من Backend أو تبقى metadata فقط."/>
    <div className="contract-list">
      {p0.map((item) => <article key={item.id}><Icon name="shield" size={18}/><div><strong>{item.title}</strong><span>{item.summary}</span></div><Badge tone="gold">{item.priority}</Badge></article>)}
    </div>
  </section>;
}

function DeferredGatePanel() {
  const deferred = LOCAL_TOOL_REGISTRY.filter((tool) => tool.status === "deferred");
  const blocked = LOCAL_TOOL_REGISTRY.filter((tool) => tool.status === "blocked");
  return <section className="section-block deferred-gate-block">
    <SectionHeading eyebrow="DEFERRED_AND_BLOCKED_TOOLS_REASSESSMENT_GATE_V1" title="بوابة المؤجل والمرفوض" detail="تُعرض هنا حتى لا تُنسى، لكنها لا تدخل التنفيذ قبل بوابة تقييم مستقلة."/>
    <div className="gate-summary-grid">
      <article><Badge tone="blue">Deferred</Badge><strong>{deferred.length}</strong><span>تحتاج مرحلة لاحقة مثل ذاكرة، OCR، Web، Sandbox.</span></article>
      <article><Badge tone="red">Blocked</Badge><strong>{blocked.length}</strong><span>تبقى محظورة حتى تفويض جديد وبوابة مخاطر.</span></article>
      <article><Badge tone="green">Next Safe Tool</Badge><strong>Document Reader</strong><span>مرشح لاحق بعد تثبيت Backend contracts.</span></article>
    </div>
  </section>;
}


type CodebaseLayerStatus = "current" | "design_only" | "future" | "blocked";

type CodebaseReadLayer = {
  id: string;
  title: string;
  status: CodebaseLayerStatus;
  source: string;
  readModel: string;
  output: string;
  boundary: string;
};

type CodebaseRoadmapStep = {
  id: string;
  title: string;
  status: CodebaseLayerStatus;
  summary: string;
  blockedUntil: string;
};

const CODEBASE_READ_MODEL_LAYERS: CodebaseReadLayer[] = [
  { id: "repository_surface", title: "Repository Surface Map", status: "current", source: "Project Reader V1", readModel: "allowed roots + key files + route matrix", output: "خريطة سطح المشروع الحالية", boundary: "Metadata فقط، بلا قراءة أسرار أو تنفيذ" },
  { id: "frontend_components", title: "Frontend Component Index", status: "design_only", source: "frontend/src", readModel: "components/pages/routes/panels", output: "فهرس واجهات React لاحق", boundary: "قراءة ملفات مسموحة فقط" },
  { id: "backend_routes", title: "Backend Route Index", status: "design_only", source: "backend/src", readModel: "FastAPI routers/endpoints/contracts", output: "فهرس API وGET/POST لاحق", boundary: "تحليل نصي/AST لاحق بلا استدعاء تشغيل" },
  { id: "tool_contracts", title: "Tool Contract Index", status: "design_only", source: "tool registry + backend contracts", readModel: "approved/deferred/blocked + authority", output: "علاقة المساعد بالأداة والحدود", boundary: "لا invoke tool" },
  { id: "agent_registry", title: "Agent Registry Index", status: "design_only", source: "agents/registry*.yaml", readModel: "assistant identity/capabilities/blocked actions", output: "فهم المساعدين والمهام المناسبة", boundary: "قراءة فقط" },
  { id: "governance_docs", title: "Governance Docs Index", status: "design_only", source: "docs/*.md", readModel: "baseline/acceptance/boundary decisions", output: "سياق حوكمة مختصر", boundary: "لا ترقية baseline تلقائية" },
  { id: "vector_rag", title: "Vector Codebase RAG", status: "future", source: "ChromaDB/LanceDB/Qdrant", readModel: "embeddings + semantic retrieval", output: "استرجاع دلالي لاحق", boundary: "غير منفذ في هذه الدفعة" },
  { id: "agent_coding", title: "Agent Coding / Self Apply", status: "blocked", source: "Shell/Git/Code execution", readModel: "غير متاح", output: "لا يوجد", boundary: "محظور حتى تفويض مستقل وبوابة مخاطر" },
];

const CODEBASE_UNDERSTANDING_ROADMAP: CodebaseRoadmapStep[] = [
  { id: "v1", title: "Read Model Design", status: "current", summary: "تثبيت طبقات الفهم ومخرجاتها وحدودها داخل الواجهة والوثائق.", blockedUntil: "مقبول الآن كتصميم فقط" },
  { id: "v2", title: "Symbol/Route/Component Index", status: "future", summary: "استخراج رموز الكود والمسارات والمكونات من الملفات المسموحة دون embeddings.", blockedUntil: "بعد قبول التصميم وإضافة Backend read-only contracts" },
  { id: "v3", title: "Codebase RAG Candidate", status: "future", summary: "إدخال فهرسة دلالية محلية عند الحاجة فقط.", blockedUntil: "بعد بوابة Vector DB منفصلة" },
  { id: "v4", title: "Engineering Agent Loop", status: "blocked", summary: "تخطيط → تعديل → اختبار → مراجعة، لكنه يتطلب Shell/Git/Code execution.", blockedUntil: "محظور في المرحلة الحالية" },
];

function codebaseTone(status: CodebaseLayerStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "current") return "green";
  if (status === "design_only") return "gold";
  if (status === "future") return "blue";
  return "red";
}

function CodebaseUnderstandingReadModelPanel() {
  const current = CODEBASE_READ_MODEL_LAYERS.filter((item) => item.status === "current").length;
  const designOnly = CODEBASE_READ_MODEL_LAYERS.filter((item) => item.status === "design_only").length;
  const future = CODEBASE_READ_MODEL_LAYERS.filter((item) => item.status === "future").length;
  const blocked = CODEBASE_READ_MODEL_LAYERS.filter((item) => item.status === "blocked").length;
  return <section className="section-block codebase-understanding-block">
    <SectionHeading eyebrow="CODEBASE_UNDERSTANDING_READ_MODEL_V1" title="نموذج فهم المشروع — تصميم/قراءة فقط" detail="هذه الطبقة تحوّل قارئ المشروع من إحصاءات سطحية إلى خريطة فهم هندسية، دون Vector DB أو LangGraph أو تنفيذ."/>
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="project" label="Current" value={current} detail="Project Reader V1 قائم" tone="gold"/>
      <MetricCard icon="review" label="Design-only" value={designOnly} detail="طبقات جاهزة للتصميم" tone="gold"/>
      <MetricCard icon="agent" label="Future" value={future} detail="RAG مؤجل" tone="blue"/>
      <MetricCard icon="lock" label="Blocked" value={blocked} detail="لا تنفيذ ذاتي" tone="red"/>
    </div>
    <div className="backend-action-grid">
      {CODEBASE_READ_MODEL_LAYERS.map((item) => <article className={`backend-action-card codebase-layer-${item.status}`} key={item.id}>
        <div className="backend-action-head"><Badge tone={codebaseTone(item.status)}>{item.status}</Badge><Badge tone="slate">read model</Badge></div>
        <strong>{item.title}</strong>
        <code>{item.source}</code>
        <p>{item.readModel}</p>
        <small>{item.boundary}</small>
      </article>)}
    </div>
  </section>;
}

function CodebaseUnderstandingRoadmapPanel() {
  return <section className="section-block codebase-roadmap-block">
    <SectionHeading eyebrow="From Project Reader to Codebase RAG" title="خارطة انتقال محكومة" detail="المحادثة الخارجية مفيدة كاتجاه معماري، لكن الأدوات الثقيلة لا تدخل إلا عبر بوابات مستقلة."/>
    <div className="lifecycle-grid">
      {CODEBASE_UNDERSTANDING_ROADMAP.map((step) => <article className="lifecycle-card" key={step.id}>
        <span>{step.id.toUpperCase()}</span>
        <strong>{step.title}</strong>
        <p>{step.summary}</p>
        <Badge tone={codebaseTone(step.status)}>{step.status}</Badge>
        <small>{step.blockedUntil}</small>
      </article>)}
    </div>
    <BoundaryPanel title="لا RAG فعلي في هذه الدفعة" detail="لا ChromaDB، لا embeddings، لا LangGraph، لا Shell، لا Git، لا تشغيل نموذج. هذه خريطة تصميم فقط فوق Project Reader المقبول."/>
  </section>;
}


type ModelCapabilityStatus = "candidate" | "design_only" | "future_gate" | "blocked";

type ModelCapabilityRole = {
  id: string;
  title: string;
  assistant: string;
  modelClass: string;
  capability: string;
  status: ModelCapabilityStatus;
  fit: string;
  boundary: string;
};

type ModelReadinessGate = {
  id: string;
  title: string;
  status: ModelCapabilityStatus;
  summary: string;
  requirement: string;
};

const LOCAL_MODEL_CAPABILITY_MATRIX: ModelCapabilityRole[] = [
  { id: "fast_triage", title: "Fast Triage Model", assistant: "error_triage_agent / coordinator", modelClass: "small local instruct model", capability: "تصنيف سريع للأخطاء والطلبات القصيرة", status: "candidate", fit: "سرعة أعلى، تكلفة موارد أقل، مناسب للفرز الأولي", boundary: "لا تنفيذ، لا Shell، لا حفظ نتائج كحقيقة" },
  { id: "coding_specialist", title: "Coding Specialist Model", assistant: "frontend_designer / backend_reader", modelClass: "coder-class local model", capability: "اقتراح كود، قراءة أنماط TypeScript/Python، وتحليل APIs", status: "design_only", fit: "يستخدم لاحقًا بعد Codebase Understanding، ولا يطبق بنفسه", boundary: "proposal-only، لا self-apply، لا Git" },
  { id: "reasoning_reviewer", title: "Reasoning / Review Model", assistant: "safety_governor / task_analyst", modelClass: "reasoning-oriented local model", capability: "مراجعة خطة، كشف تناقضات، فحص حدود", status: "design_only", fit: "مناسب لمرحلة Accepted as Plan وليس Apply", boundary: "لا يقرر التفويض بدل المستخدم" },
  { id: "arabic_governance", title: "Arabic Governance Model", assistant: "documentation_handoff / evidence_baseline_keeper", modelClass: "Arabic-capable instruct model", capability: "صياغة عربية، تلخيص توريث، تبسيط أدلة", status: "design_only", fit: "يرفع جودة مخرجات التوثيق والتواصل", boundary: "لا baseline promotion تلقائي" },
  { id: "document_summarizer", title: "Document / Knowledge Model", assistant: "documentation_handoff لاحقًا", modelClass: "summarization/information extraction model", capability: "تلخيص مستندات واستخراج بنود لاحقًا", status: "future_gate", fit: "بعد Document Reader، وقبل أي OCR أو RAG", boundary: "لا OCR ولا Vector DB الآن" },
  { id: "cloud_frontier", title: "Cloud Frontier Models", assistant: "غير مفعّل", modelClass: "external cloud model", capability: "قدرات خام أعلى لكن خارج الخصوصية المحلية", status: "blocked", fit: "ليس مسار التشغيل المحلي الحالي", boundary: "لا إرسال كود أو ملفات لخارج الجهاز" },
];

const LOCAL_MODEL_READINESS_GATES: ModelReadinessGate[] = [
  { id: "inventory", title: "Local Model Inventory", status: "future_gate", summary: "قراءة أسماء النماذج المحلية المتاحة دون تشغيلها.", requirement: "عقد GET-only مستقل، ولا يستدعي النموذج" },
  { id: "role_mapping", title: "Role-to-Model Mapping", status: "candidate", summary: "ربط كل مساعد بفئة نموذج مناسبة بدل نموذج واحد للجميع.", requirement: "يعتمد على مصفوفة القدرات الحالية" },
  { id: "prompt_contract", title: "Prompt / Output Contract", status: "design_only", summary: "تحديد مخرجات JSON/Markdown آمنة قبل أي تجربة نموذج.", requirement: "لا قبول لمخرجات حرة في التشغيل اللاحق" },
  { id: "resource_gate", title: "Hardware & Resource Gate", status: "future_gate", summary: "تقدير RAM/VRAM/CPU قبل السماح بأي Pilot.", requirement: "قراءة فقط أو إدخال يدوي؛ لا benchmark الآن" },
  { id: "pilot_uat", title: "Controlled Local Model Pilot", status: "blocked", summary: "تجربة نموذج محلية مقيدة على مهام غير حساسة.", requirement: "تفويض مستقل + UAT + no self-apply" },
];

function modelTone(status: ModelCapabilityStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "candidate") return "green";
  if (status === "design_only") return "gold";
  if (status === "future_gate") return "blue";
  return "red";
}

function LocalModelStrategyMatrixPanel() {
  const candidate = LOCAL_MODEL_CAPABILITY_MATRIX.filter((item) => item.status === "candidate").length;
  const designOnly = LOCAL_MODEL_CAPABILITY_MATRIX.filter((item) => item.status === "design_only").length;
  const future = LOCAL_MODEL_CAPABILITY_MATRIX.filter((item) => item.status === "future_gate").length;
  const blocked = LOCAL_MODEL_CAPABILITY_MATRIX.filter((item) => item.status === "blocked").length;
  return <section className="section-block model-strategy-block">
    <SectionHeading eyebrow="LOCAL_MODEL_STRATEGY_AND_CAPABILITY_MATRIX_V1" title="استراتيجية النماذج المحلية — تصميم فقط" detail="لا نختار نموذجًا واحدًا لكل شيء. نحدد فئة النموذج المناسبة لكل مساعد، مع بقاء التشغيل محجوبًا."/>
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="agent" label="Candidate" value={candidate} detail="مرشح كدور، لا تشغيل" tone="gold"/>
      <MetricCard icon="review" label="Design-only" value={designOnly} detail="محدد نظريًا" tone="gold"/>
      <MetricCard icon="project" label="Future gate" value={future} detail="يحتاج بوابة لاحقة" tone="blue"/>
      <MetricCard icon="lock" label="Blocked" value={blocked} detail="خارج النطاق" tone="red"/>
    </div>
    <div className="model-matrix-grid">
      {LOCAL_MODEL_CAPABILITY_MATRIX.map((item) => <article className="model-matrix-card" key={item.id}>
        <div className="backend-action-head"><Badge tone={modelTone(item.status)}>{item.status}</Badge><Badge tone="slate">model class</Badge></div>
        <strong>{item.title}</strong>
        <code>{item.modelClass}</code>
        <p>{item.capability}</p>
        <small><b>المساعد:</b> {item.assistant}</small>
        <small><b>الملاءمة:</b> {item.fit}</small>
        <em>{item.boundary}</em>
      </article>)}
    </div>
    <BoundaryPanel title="قوة الوكيل لا تأتي من النموذج وحده" detail="الفعالية المستقبلية ستأتي من: نموذج مناسب + أدوات محكومة + فهم الكود + دورة مراجعة. هذه الدفعة لا تشغل Ollama ولا DeepSeek ولا أي نموذج آخر."/>
  </section>;
}

function LocalModelReadinessGatePanel() {
  return <section className="section-block model-readiness-block">
    <SectionHeading eyebrow="MODEL RUNTIME READINESS — NOT YET" title="بوابات ما قبل تشغيل النموذج" detail="هذه قائمة إجراءات لاحقة تمنع القفز من التصميم إلى التشغيل بلا ضبط."/>
    <div className="lifecycle-grid">
      {LOCAL_MODEL_READINESS_GATES.map((gate) => <article className="lifecycle-card" key={gate.id}>
        <span>{gate.id.slice(0, 2).toUpperCase()}</span>
        <strong>{gate.title}</strong>
        <p>{gate.summary}</p>
        <Badge tone={modelTone(gate.status)}>{gate.status}</Badge>
        <small>{gate.requirement}</small>
      </article>)}
    </div>
    <BoundaryPanel title="لا Model Pilot في هذه الدفعة" detail="أي تشغيل نموذج لاحق يحتاج تفويضًا مستقلًا، عقد مخرجات، عينة UAT، وسجل حدود. لا self-apply ولا تشغيل كود من مخرجات النموذج."/>
  </section>;
}



type GoalPlanStatus = "intake" | "design_only" | "future_gate" | "blocked";

type GoalPlanLayer = {
  id: string;
  title: string;
  status: GoalPlanStatus;
  owner: string;
  output: string;
  guardrail: string;
};

type GoalToolSelection = {
  id: string;
  taskType: string;
  candidateTools: string[];
  selectedAssistants: string[];
  result: string;
  boundary: string;
};

const GOAL_TO_PLAN_LAYERS: GoalPlanLayer[] = [
  { id: "goal_intake", title: "Goal Intake", status: "intake", owner: "coordinator / task_analyst", output: "هدف منظم، نطاق، افتراضات، وقيود", guardrail: "لا إرسال للهدف إلى نموذج أو خدمة" },
  { id: "goal_analyzer", title: "Goal Analyzer", status: "design_only", owner: "task_analyst", output: "تصنيف نوع المشروع: frontend/backend/full-stack/docs", guardrail: "تحليل تصميمي فقط" },
  { id: "project_plan_draft", title: "Project Plan Draft", status: "design_only", owner: "coordinator", output: "مهام مرحلية قابلة للمراجعة", guardrail: "الخطة ليست Apply ولا Execution" },
  { id: "tool_selection_matrix", title: "Tool Selection Matrix", status: "design_only", owner: "safety_governor + tool_registry", output: "ربط كل مهمة بالأدوات المسموحة أو المؤجلة", guardrail: "اختيار الأداة لا يعني invoke" },
  { id: "human_review_gate", title: "Human Review Gate", status: "future_gate", owner: "reviewer / operator", output: "قبول كخطة أو إرجاع للتوضيح", guardrail: "المراجعة تفصل الخطة عن التنفيذ" },
  { id: "autonomous_execution", title: "Autonomous Build / Execution", status: "blocked", owner: "غير مفعّل", output: "لا يوجد", guardrail: "محظور: Shell/Git/Code/Model/Pilot/self-apply" },
];

const GOAL_TOOL_SELECTION_MATRIX: GoalToolSelection[] = [
  { id: "scope", taskType: "تحليل النطاق والمتطلبات", candidateTools: ["task_planner", "tool_registry"], selectedAssistants: ["coordinator", "task_analyst"], result: "Goal brief + acceptance criteria", boundary: "prepare-only" },
  { id: "repo_map", taskType: "فهم المشروع الحالي", candidateTools: ["project_reader", "route_api_reader"], selectedAssistants: ["project_reader", "backend_reader"], result: "Repository surface + route matrix", boundary: "read-only" },
  { id: "frontend", taskType: "تصميم واجهة أو شاشة", candidateTools: ["task_planner", "project_reader"], selectedAssistants: ["frontend_designer", "ux_reviewer"], result: "UI proposal + component plan", boundary: "proposal-only" },
  { id: "backend", taskType: "تحديد عقود Backend/API", candidateTools: ["route_api_reader", "tool_registry"], selectedAssistants: ["backend_reader", "safety_governor"], result: "API contract draft", boundary: "no backend mutation" },
  { id: "review", taskType: "مراجعة الخطة قبل أي بناء", candidateTools: ["evidence_summarizer", "task_planner"], selectedAssistants: ["safety_governor", "uat_tester"], result: "Accepted as Plan / Returned", boundary: "review is not execution" },
  { id: "blocked_run", taskType: "تنفيذ المشروع أو تشغيل أوامر", candidateTools: ["shell_execution", "git_operations", "code_execution", "model_execution"], selectedAssistants: ["غير مفعّل"], result: "Blocked", boundary: "requires future separate gates" },
];

function goalTone(status: GoalPlanStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "intake") return "green";
  if (status === "design_only") return "gold";
  if (status === "future_gate") return "blue";
  return "red";
}

function GoalToPlanToolSelectionPanel({ compact = false }: { compact?: boolean }) {
  const intake = GOAL_TO_PLAN_LAYERS.filter((item) => item.status === "intake").length;
  const designOnly = GOAL_TO_PLAN_LAYERS.filter((item) => item.status === "design_only").length;
  const future = GOAL_TO_PLAN_LAYERS.filter((item) => item.status === "future_gate").length;
  const blocked = GOAL_TO_PLAN_LAYERS.filter((item) => item.status === "blocked").length;
  return <section className="section-block goal-plan-block">
    <SectionHeading eyebrow="GOAL_TO_PLAN_TOOL_SELECTION_V1" title="من الهدف إلى الخطة واختيار الأدوات — تصميم فقط" detail="هذه الطبقة تجهز طريقة استقبال هدف كبير وتحويله إلى خطة ومصفوفة أدوات، بدون بناء ذاتي أو تشغيل أوامر أو نموذج."/>
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="task" label="Goal intake" value={intake} detail="نموذج هدف محكوم" tone="gold"/>
      <MetricCard icon="tool" label="Design-only" value={designOnly} detail="تحليل وخطة ومصفوفة" tone="gold"/>
      <MetricCard icon="review" label="Future gate" value={future} detail="مراجعة بشرية لاحقة" tone="blue"/>
      <MetricCard icon="lock" label="Blocked" value={blocked} detail="لا بناء ذاتي" tone="red"/>
    </div>
    <div className="lifecycle-grid goal-layer-grid">
      {GOAL_TO_PLAN_LAYERS.map((layer) => <article className="lifecycle-card" key={layer.id}>
        <span>{layer.id.slice(0, 2).toUpperCase()}</span>
        <strong>{layer.title}</strong>
        <p>{layer.output}</p>
        <Badge tone={goalTone(layer.status)}>{layer.status}</Badge>
        <small>{layer.guardrail}</small>
      </article>)}
    </div>
    {!compact && <ToolSelectionMatrixPanel />}
    <BoundaryPanel title="اختيار الأداة ليس تشغيلًا" detail="الدفعة لا تستخدم LangGraph فعليًا، لا تستدعي نموذجًا، لا تشغل Shell أو Git، ولا تبني مشروعًا جديدًا. هي نموذج قرار وخطة قابلة للمراجعة فقط."/>
  </section>;
}

function ToolSelectionMatrixPanel() {
  return <section className="tool-selection-matrix" aria-label="مصفوفة اختيار الأدوات">
    <SectionHeading eyebrow="Dynamic Tool Registry — Design" title="مصفوفة ربط نوع المهمة بالأدوات والمساعدين" detail="كل صف يوضح ما سيقترحه الوكيل لاحقًا عند تحليل الهدف. الأدوات المحظورة تظهر كـBlocked فقط."/>
    <div className="tool-selection-list">
      {GOAL_TOOL_SELECTION_MATRIX.map((row) => <article className="tool-selection-row" key={row.id}>
        <div><strong>{row.taskType}</strong><span>{row.result}</span></div>
        <div className="tool-chip-row wide">{row.candidateTools.map((toolId) => <span key={toolId}>{getToolById(toolId)?.name ?? toolId}</span>)}</div>
        <small>{row.selectedAssistants.join(" / ")}</small>
        <Badge tone={row.result === "Blocked" ? "red" : "gold"}>{row.boundary}</Badge>
      </article>)}
    </div>
  </section>;
}

function GoalPlanner() {
  const [goal, setGoal] = useState("ابنِ نظام إدارة مهام داخلي بواجهة عربية، Backend API، وصلاحيات مراجعة قبل التنفيذ");
  const normalizedGoal = goal.trim() || "هدف غير محدد";
  return <Layout eyebrow="Goal Intake" title="مخطط الأهداف واختيار الأدوات">
    <section className="page-intro goal-planner-intro"><span className="intro-icon"><Icon name="task" size={24}/></span><div><p>تصميم فقط</p><h2>أعطِ هدفًا كبيرًا، وشاهد كيف سيتحوّل لاحقًا إلى خطة وأدوات</h2><span>هذه الشاشة لا تستدعي نموذجًا ولا تبني مشروعًا. هي واجهة تحضيرية لمسار Goal → Plan → Tool Selection.</span></div></section>
    <section className="content-grid primary-grid goal-intake-grid">
      <article className="composer-card goal-intake-card">
        <div className="composer-head"><div><p>Goal Intake Form</p><h2>نموذج الهدف العالي المستوى</h2><span>المدخل يبقى داخل المتصفح للعرض فقط، ولا يرسل إلى Backend أو نموذج.</span></div><Badge tone="gold">Design-only</Badge></div>
        <div className="form-grid">
          <label className="wide">الهدف<textarea value={goal} onChange={(event) => setGoal(event.target.value)} /></label>
          <label>نوع المشروع<input value="Full-stack / governed local agents" disabled readOnly /></label>
          <label>سلطة التنفيذ<input value="NONE — review only" disabled readOnly /></label>
        </div>
        <div className="composer-actions"><DisabledButton icon="lock">توليد مشروع — محجوب</DisabledButton><DisabledButton icon="agent">تحليل بواسطة نموذج — محجوب</DisabledButton></div>
      </article>
      <article className="reader-panel goal-preview-card">
        <SectionHeading eyebrow="Project Plan Draft" title="مسودة خطة قابلة للمراجعة" detail="هذه عينة بنيوية ثابتة لتوضيح شكل المخرج المتوقع لاحقًا."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>الهدف</strong><span>{normalizedGoal}</span></div>
          <div className="reader-row"><strong>النطاق</strong><span>تحليل → خطة → اختيار أدوات → مراجعة بشرية</span></div>
          <div className="reader-row"><strong>الأدوات</strong><span>Tool Registry / Project Reader / Task Planner</span></div>
          <div className="reader-row"><strong>المحظورات</strong><span>Shell / Git / Code execution / Model / Pilot</span></div>
        </div>
      </article>
    </section>
    <GoalToPlanToolSelectionPanel />
    <ProjectRealityCharterPanel compact />
    <ProjectStateManagerPanel compact />
    <BoundaryPanel title="Goal Planner ليس مصنع برمجيات ذاتي الآن" detail="هذا تصميم لمسار مصنع البرمجيات لاحقًا، لكنه لا يكتب ملفات، لا يشغل اختبارات، لا يستخدم Git، ولا يسمح self-apply."/>
  </Layout>;
}


type ProjectRealityStatus = "foundation" | "governance" | "future_gate" | "blocked";

type ProjectRealityPrinciple = {
  id: string;
  title: string;
  status: ProjectRealityStatus;
  statement: string;
  operationalMeaning: string;
  guardrail: string;
};

type ProjectRealityMilestone = {
  id: string;
  title: string;
  currentState: string;
  nextUse: string;
};

const PROJECT_REALITY_PRINCIPLES: ProjectRealityPrinciple[] = [
  { id: "platform_identity", title: "Governed Local Engineering Agentic Platform", status: "foundation", statement: "الحقيقة الرسمية: ليست أداة دردشة، بل منصة هندسية محلية محكومة.", operationalMeaning: "تستقبل هدفًا، تنظمه، تقترح خطة وأدوات، وتعرض قرار مراجعة قبل أي تنفيذ.", guardrail: "لا تشغيل خفي ولا انتقال آلي من الخطة إلى التطبيق" },
  { id: "human_authority", title: "Human Authority", status: "governance", statement: "المستخدم هو صاحب القرار والسيادة النهائية.", operationalMeaning: "كل خطة أو قبول أو انتقال يحتاج مراجعة بشرية صريحة.", guardrail: "لا تفويض ضمني من نجاح الواجهة أو صحة الخدمة" },
  { id: "goal_to_plan", title: "Goal-to-Plan First", status: "foundation", statement: "الهدف العالي المستوى يتحول أولًا إلى خطة قابلة للمراجعة.", operationalMeaning: "Goal Intake → Project Plan Draft → Tool Selection Matrix → Human Review Gate.", guardrail: "الخطة ليست تنفيذًا وليست بناء مشروع" },
  { id: "tool_contracts", title: "Tool Contracts", status: "governance", statement: "كل أداة تُفهم من عقدها وحدودها لا من اسمها فقط.", operationalMeaning: "الأدوات المقبولة تقترح وتقرأ وتحضر؛ الأدوات المؤجلة أو المحجوبة لا تعمل.", guardrail: "اختيار الأداة لا يعني invoke" },
  { id: "local_privacy", title: "Local Sovereignty & Privacy", status: "foundation", statement: "الخصوصية المحلية أصل تأسيسي وليست ميزة تجميلية.", operationalMeaning: "لا إرسال كود أو وثائق أو أهداف إلى خدمات خارجية ضمن هذه المرحلة.", guardrail: "Cloud frontier models تبقى خارج المسار المحلي الحالي" },
  { id: "auditability", title: "Audit Trail Before Autonomy", status: "future_gate", statement: "أي تنفيذ مستقبلي يجب أن يكون قابلًا للتدقيق والاسترجاع.", operationalMeaning: "قبل التنفيذ نحتاج State Manager، سجل قرارات، مخرجات محددة، وUAT.", guardrail: "لا autonomous build قبل بوابة مستقلة" },
  { id: "no_self_apply", title: "No Self-Apply", status: "blocked", statement: "الوكيل لا يطبق على نفسه ولا يغيّر المشروع ذاتيًا.", operationalMeaning: "أي تطبيق يبقى عبر حزمة محكومة وتفويض صريح ومراجعة بشرية.", guardrail: "Self-apply / hidden execution / silent mutation = blocked" },
  { id: "execution_layer", title: "Execution Is Future-Gated", status: "blocked", statement: "طبقة التنفيذ مؤجلة ومغلقة حاليًا.", operationalMeaning: "لا Shell، لا Git، لا Code execution، لا Model/Pilot، لا DB persistence.", guardrail: "التصميم الحالي prepare/read-only فقط" },
];

const PROJECT_REALITY_MILESTONES: ProjectRealityMilestone[] = [
  { id: "screen", title: "Operational Frontend", currentState: "مقبول بصريًا", nextUse: "واجهة تشغيل مفهومة لا واجهة حوكمة فقط" },
  { id: "backend_alignment", title: "Backend/Frontend Alignment", currentState: "مقبول", nextUse: "عقود خادمية تحمي الواجهة من الوهم التشغيلي" },
  { id: "review_flow", title: "Task Draft Review Flow", currentState: "مقبول", nextUse: "فصل Draft عن Accepted as Plan وعن التنفيذ" },
  { id: "codebase", title: "Codebase Understanding Read Model", currentState: "مقبول", nextUse: "الانتقال من قارئ مشروع إلى فهم هندسي محكوم" },
  { id: "models", title: "Local Model Strategy Matrix", currentState: "مقبول", nextUse: "اختيار دور النموذج قبل تشغيل أي نموذج" },
  { id: "goal_plan", title: "Goal-to-Plan Tool Selection", currentState: "مقبول مع إصلاح Route", nextUse: "تحويل الأهداف الكبيرة إلى خطط وأدوات ومراجعة" },
  { id: "charter", title: "Project Reality Charter", currentState: "هذه الدفعة", nextUse: "تثبيت الحقيقة الحاكمة للمشروع داخل الواجهة والوثائق" },
];

function realityTone(status: ProjectRealityStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "foundation") return "green";
  if (status === "governance") return "gold";
  if (status === "future_gate") return "blue";
  return "red";
}

function ProjectRealityCharterPanel({ compact = false }: { compact?: boolean }) {
  const foundation = PROJECT_REALITY_PRINCIPLES.filter((item) => item.status === "foundation").length;
  const governance = PROJECT_REALITY_PRINCIPLES.filter((item) => item.status === "governance").length;
  const future = PROJECT_REALITY_PRINCIPLES.filter((item) => item.status === "future_gate").length;
  const blocked = PROJECT_REALITY_PRINCIPLES.filter((item) => item.status === "blocked").length;
  return <section className="section-block project-reality-block">
    <SectionHeading eyebrow="PROJECT_REALITY_AND_GOVERNING_CHARTER_V1" title="الحقيقة الحاكمة للمشروع" detail="هذه الدفعة تثبت أن المشروع منصة هندسية محلية محكومة، لا وكيلًا منفلتًا ولا مجرد شاشة أدوات."/>
    <div className="charter-statement">
      <strong>Governed Local Engineering Agentic Platform</strong>
      <p>مصنع برمجيات محلي محكوم: يفهم الهدف، يحوله إلى خطة، يختار الأدوات، يطلب مراجعة بشرية، ولا ينفذ أو يطبق إلا عبر بوابات مستقلة لاحقة.</p>
    </div>
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="project" label="Foundation" value={foundation} detail="هوية واتجاه" tone="gold"/>
      <MetricCard icon="shield" label="Governance" value={governance} detail="قرار وحدود" tone="gold"/>
      <MetricCard icon="review" label="Future gates" value={future} detail="ما قبل التنفيذ" tone="blue"/>
      <MetricCard icon="lock" label="Blocked" value={blocked} detail="لا self-apply" tone="red"/>
    </div>
    <div className="backend-action-grid charter-principles-grid">
      {PROJECT_REALITY_PRINCIPLES.map((principle) => <article className={`backend-action-card charter-principle-${principle.status}`} key={principle.id}>
        <div className="backend-action-head"><Badge tone={realityTone(principle.status)}>{principle.status}</Badge><Badge tone="slate">charter</Badge></div>
        <strong>{principle.title}</strong>
        <p>{principle.statement}</p>
        <small>{principle.operationalMeaning}</small>
        <em>{principle.guardrail}</em>
      </article>)}
    </div>
    {!compact && <ProjectRealityMilestonesPanel />}
    <BoundaryPanel title="الرؤية لا تمنح تنفيذًا" detail="هذه الدفعة Design-only. لا Model، لا Pilot، لا Shell، لا Git، لا Code execution، لا DB persistence، ولا self-apply. الحقيقة الحاكمة تضبط ما سيأتي ولا تفتحه."/>
  </section>;
}

function ProjectRealityMilestonesPanel() {
  return <section className="charter-milestones" aria-label="خريطة نضج المشروع">
    <SectionHeading eyebrow="Accepted Foundations" title="ما الذي بُني حتى الآن لخدمة الحقيقة؟" detail="هذه ليست Baseline promotion؛ إنها خريطة تشغيلية مرئية للمراحل المقبولة وما تستخدم له لاحقًا."/>
    <div className="lifecycle-grid charter-milestone-grid">
      {PROJECT_REALITY_MILESTONES.map((milestone) => <article className="lifecycle-card" key={milestone.id}>
        <span>{milestone.id.slice(0, 2).toUpperCase()}</span>
        <strong>{milestone.title}</strong>
        <p>{milestone.nextUse}</p>
        <Badge tone={milestone.id === "charter" ? "gold" : "green"}>{milestone.currentState}</Badge>
      </article>)}
    </div>
  </section>;
}

function ProjectRealityCharter() {
  return <Layout eyebrow="Governing Charter" title="الحقيقة الحاكمة للمشروع">
    <section className="page-intro charter-intro"><span className="intro-icon"><Icon name="shield" size={24}/></span><div><p>PROJECT_REALITY_AND_GOVERNING_CHARTER_V1</p><h2>منصة هندسية محلية محكومة، لا تنفيذ ذاتي منفلت</h2><span>هذه الصفحة تثبت هوية المشروع ومبادئه وحدوده قبل أي انتقال لاحق إلى State Manager أو Model Pilot أو Execution Layer.</span></div></section>
    <ProjectRealityCharterPanel />
    <ProjectStateManagerPanel compact />
    <section className="content-grid primary-grid">
      <article className="reader-panel">
        <SectionHeading eyebrow="What it is" title="ما يجب أن يصبح عليه المشروع" detail="صياغة عملية لا فلسفية فقط."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>النوع</strong><span>Governed Local Engineering Agentic Platform</span></div>
          <div className="reader-row"><strong>الوظيفة</strong><span>هدف → خطة → أدوات → مراجعة → تنفيذ لاحق مشروط</span></div>
          <div className="reader-row"><strong>صاحب القرار</strong><span>المستخدم/المطور</span></div>
          <div className="reader-row"><strong>الخصوصية</strong><span>محلية أولًا، لا تسريب كود أو وثائق</span></div>
        </div>
      </article>
      <article className="reader-panel danger-panel">
        <SectionHeading eyebrow="What it is not" title="ما لا يجب أن يتحول إليه" detail="الحدود السلبية تمنع الانحراف المعماري."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>ليس</strong><span>Chat عام</span></div>
          <div className="reader-row"><strong>ليس</strong><span>Agent self-apply</span></div>
          <div className="reader-row"><strong>ليس</strong><span>تشغيل Shell/Git/Code خفي</span></div>
          <div className="reader-row"><strong>ليس</strong><span>اعتمادًا أعمى على نموذج محلي أو سحابي</span></div>
        </div>
      </article>
    </section>
  </Layout>;
}


type ProjectStateSliceStatus = "declared" | "prepared" | "review" | "future_gate" | "blocked";

type ProjectStateSlice = {
  id: string;
  title: string;
  status: ProjectStateSliceStatus;
  source: string;
  payload: string;
  nextGate: string;
  persistence: string;
};

type ProjectStateTransition = {
  from: string;
  to: string;
  gate: string;
  allowedNow: boolean;
  reason: string;
};

const PROJECT_STATE_SLICES: ProjectStateSlice[] = [
  { id: "goal", title: "Goal State", status: "prepared", source: "Goal Intake / goal-planner", payload: "الهدف العالي المستوى والنطاق الأولي", nextGate: "Human review before plan acceptance", persistence: "none — browser/display only" },
  { id: "plan", title: "Plan Draft State", status: "prepared", source: "Project Plan Draft", payload: "مهام مقترحة ومراحل تنفيذ مستقبلية", nextGate: "Accepted as Plan", persistence: "none" },
  { id: "tool_selection", title: "Tool Selection State", status: "declared", source: "Tool Selection Matrix", payload: "ربط نوع المهمة بالأداة والمساعد المناسب", nextGate: "Tool contract review", persistence: "none" },
  { id: "task_drafts", title: "Task Drafts State", status: "review", source: "Backend prepare + local view", payload: "Draft / Ready for Review / Returned / Accepted as Plan", nextGate: "Review gate only", persistence: "none — local display" },
  { id: "review", title: "Review Status State", status: "review", source: "Task Draft Review Flow", payload: "قرار بشري قبل أي انتقال", nextGate: "No execution transition yet", persistence: "none" },
  { id: "charter", title: "Charter Boundary State", status: "blocked", source: "Project Reality Charter", payload: "No self-apply, no hidden execution, execution future-gated", nextGate: "Independent authorization gate", persistence: "docs only" },
  { id: "runtime", title: "Runtime/Execution State", status: "blocked", source: "Pilot Control", payload: "Model/Pilot/Shell/Git/Code execution مغلقة", nextGate: "Future runtime readiness", persistence: "none" },
];

const PROJECT_STATE_TRANSITIONS: ProjectStateTransition[] = [
  { from: "Goal", to: "Plan Draft", gate: "Goal Intake", allowedNow: true, reason: "تحويل بصري/بنيوي فقط، بلا نموذج أو تنفيذ" },
  { from: "Plan Draft", to: "Tool Selection", gate: "Tool Matrix", allowedNow: true, reason: "اختيار أدوات مقترح من عقود ثابتة فقط" },
  { from: "Tool Selection", to: "Task Draft", gate: "Backend prepare", allowedNow: true, reason: "يعيد draft envelope فقط؛ persistence=none" },
  { from: "Task Draft", to: "Accepted as Plan", gate: "Human Review", allowedNow: true, reason: "قرار مراجعة لا يفتح التنفيذ" },
  { from: "Accepted as Plan", to: "Apply/Execution", gate: "Execution Authorization", allowedNow: false, reason: "محجوب حتى Project State persistence + Audit Trail + Runtime Gate" },
  { from: "Any State", to: "Self-Apply", gate: "None", allowedNow: false, reason: "مرفوض صراحة في Charter" },
];

function projectStateTone(status: ProjectStateSliceStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "prepared") return "blue";
  if (status === "review") return "gold";
  if (status === "declared") return "green";
  if (status === "future_gate") return "slate";
  return "red";
}

function ProjectStateManagerPanel({ compact = false }: { compact?: boolean }) {
  const prepared = PROJECT_STATE_SLICES.filter((item) => item.status === "prepared").length;
  const review = PROJECT_STATE_SLICES.filter((item) => item.status === "review").length;
  const blocked = PROJECT_STATE_SLICES.filter((item) => item.status === "blocked").length;
  return <section className="section-block project-state-manager-block">
    <SectionHeading eyebrow="PROJECT_STATE_MANAGER_V1" title="مدير حالة المشروع" detail="نموذج حالة واحد يجمع الهدف والخطة والأدوات والمسودات والمراجعة والحدود، Design-only دون حفظ دائم."/>
    <div className="project-state-summary">
      <article><strong>State Model</strong><span>Goal → Plan Draft → Tool Selection → Task Drafts → Review Status → Charter Boundaries</span></article>
      <article><strong>Persistence</strong><span>NONE الآن — لا SQLite ولا DB ولا ملف تشغيل دائم</span></article>
      <article><strong>Resume</strong><span>Prepared concept فقط؛ الاستئناف الفعلي يحتاج تفويض تخزين لاحق</span></article>
    </div>
    <div className="metrics-grid compact-metrics">
      <MetricCard icon="project" label="State slices" value={PROJECT_STATE_SLICES.length} detail="نموذج موحد" tone="blue"/>
      <MetricCard icon="task" label="Prepared" value={prepared} detail="خطة/هدف فقط" tone="blue"/>
      <MetricCard icon="review" label="Review" value={review} detail="قرار بشري" tone="gold"/>
      <MetricCard icon="lock" label="Blocked" value={blocked} detail="تنفيذ محجوب" tone="red"/>
    </div>
    <div className="state-slice-grid">
      {PROJECT_STATE_SLICES.map((slice) => <article className="state-slice-card" key={slice.id}>
        <div><Badge tone={projectStateTone(slice.status)}>{slice.status}</Badge><Badge tone="slate">{slice.persistence}</Badge></div>
        <strong>{slice.title}</strong>
        <p>{slice.payload}</p>
        <small>Source: {slice.source}</small>
        <em>Next gate: {slice.nextGate}</em>
      </article>)}
    </div>
    {!compact && <ProjectStateTransitionPanel />}
    <BoundaryPanel title="Project State لا يساوي تخزينًا دائمًا" detail="هذه الدفعة تعرف الحالة وتعرضها فقط. لا SQLite، لا DB، لا كتابة runtime، لا تنفيذ. أي حفظ دائم يحتاج دفعة مستقلة."/>
  </section>;
}

function ProjectStateTransitionPanel() {
  return <section className="state-transition-panel">
    <SectionHeading eyebrow="Transition Policy" title="انتقالات الحالة المسموحة والمحجوبة" detail="يوضح هذا الجدول أين تقف الحدود بين الخطة والمراجعة والتنفيذ."/>
    <div className="state-transition-list">
      {PROJECT_STATE_TRANSITIONS.map((transition) => <article className={transition.allowedNow ? "state-transition-row" : "state-transition-row blocked"} key={`${transition.from}-${transition.to}`}>
        <span><strong>{transition.from}</strong><i>→</i><strong>{transition.to}</strong></span>
        <Badge tone={transition.allowedNow ? "green" : "red"}>{transition.allowedNow ? "allowed as design/review" : "blocked"}</Badge>
        <small>{transition.gate}</small>
        <p>{transition.reason}</p>
      </article>)}
    </div>
  </section>;
}

function ProjectStateManager() {
  return <Layout eyebrow="Project State" title="مدير حالة المشروع">
    <section className="page-intro state-manager-intro"><span className="intro-icon"><Icon name="project" size={24}/></span><div><p>PROJECT_STATE_MANAGER_V1_DESIGN_ONLY</p><h2>حالة موحدة قبل أي استئناف أو تنفيذ</h2><span>هذه الصفحة تجمع الهدف والخطة والأدوات والمسودات والمراجعة والحدود في نموذج واحد، لكنها لا تحفظ دائمًا ولا تنفذ.</span></div></section>
    <ProjectStateManagerPanel />
    <section className="content-grid primary-grid">
      <article className="reader-panel">
        <SectionHeading eyebrow="State Snapshot" title="لقطة الحالة المفاهيمية" detail="هذه صيغة حالة مستقبلية؛ ليست سجلًا محفوظًا بعد."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>goal_state</strong><span>declared/prepared</span></div>
          <div className="reader-row"><strong>plan_draft_state</strong><span>prepared / review pending</span></div>
          <div className="reader-row"><strong>tool_selection_state</strong><span>contract-mapped only</span></div>
          <div className="reader-row"><strong>review_state</strong><span>human authority required</span></div>
          <div className="reader-row"><strong>execution_state</strong><span>blocked / future-gated</span></div>
        </div>
      </article>
      <article className="reader-panel danger-panel">
        <SectionHeading eyebrow="Persistence Gate" title="ما الذي نحتاجه قبل الحفظ؟" detail="أي حفظ دائم ليس ضمن هذه الدفعة."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>Schema</strong><span>Local Task Store أو SQLite لاحقًا</span></div>
          <div className="reader-row"><strong>Audit</strong><span>state transition log</span></div>
          <div className="reader-row"><strong>Rollback</strong><span>استرجاع snapshot</span></div>
          <div className="reader-row"><strong>Approval</strong><span>تفويض مستقل مطلوب</span></div>
        </div>
      </article>
    </section>
  </Layout>;
}

function CommandCenter() {
  const dashboard = useRead<UnknownRecord>("/api/v1/local-agents/dashboard");
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  const health = useRead<UnknownRecord>("/health");
  return <Layout eyebrow="لوحة تشغيل مرئية" title="مركز المساعدين المحليين">
    <section className="welcome-hero screen-first-hero">
      <div className="hero-copy">
        <div className="eyebrow-line"><span className="live-dot"/> Screen-first Operational Console V1</div>
        <h2>شاشة تشغيل مفهومة قبل أي حوكمة إضافية</h2>
        <p>هذه الواجهة تعطيك مسارًا عمليًا: اختر مساعدًا، صغ مهمة، راجع المخرج. كل ذلك ما زال قراءة وتحضيرًا مرئيًا فقط؛ لا تنفيذ، لا كتابة، لا نموذج.</p>
        <div className="hero-pills"><span><Icon name="agent" size={15}/> مساعدون واضحون</span><span><Icon name="task" size={15}/> مهمة مرئية</span><span><Icon name="shield" size={15}/> حدود ثابتة</span></div>
      </div>
      <aside className="hero-guardrail"><div className="guardrail-top"><span className="guardrail-icon"><Icon name="shield" size={22}/></span><div><p>حالة التشغيل</p><strong>آمن ومقروء</strong></div></div><dl><div><dt>الواجهة</dt><dd>تشغيلية</dd></div><div><dt>النموذج</dt><dd>غير منفذ</dd></div><div><dt>الكتابة</dt><dd>محجوبة</dd></div></dl></aside>
    </section>

    <StartHerePanel />
    <FrontendMegaOverviewPanel />
    <GoalToPlanToolSelectionPanel compact />
    <ProjectRealityCharterPanel compact />
    <ProjectStateManagerPanel compact />

    <StateGate state={dashboard} label="ملخص المنصة">
      {(data) => {
        const record = asRecord(data);
        const counts = asRecord(record.counts);
        const approved = count(counts.approved);
        const evidenceDisclosure = asRecord(record.evidence_disclosure);
        const evidence = evidenceDisclosure.canonical_records_available === true ? count(counts.evidence) : "غير منشور";
        const posture = safeStatus(asRecord(record.system_posture).MODEL_EXECUTION, "NONE");
        return <section className="metrics-grid" aria-label="ملخص تشغيل المنصة">
          <MetricCard icon="workspace" label="مساحات العمل" value="عرض محكوم" detail="السياق ظاهر دون تبديل أو كتابة" tone="blue"/>
          <MetricCard icon="task" label="مهام معتمدة" value={approved} detail="مقروءة فقط — غير منفذة" tone="gold"/>
          <MetricCard icon="evidence" label="أدلة تشغيلية" value={evidence} detail="لا مسارات محلية في المتصفح" tone="slate"/>
          <MetricCard icon="agent" label="تنفيذ النموذج" value={posture} detail="يبقى محجوبًا" tone="red"/>
        </section>;
      }}
    </StateGate>

    <section className="content-grid primary-grid">
      <TaskComposerMock />
      <BoundaryPanel title="الشاشة عملية لكنها لا تنفذ" detail="الأزرار المرئية مقفلة عمدًا. الهدف الآن أن تفهم دورة العمل قبل فتح أي Actor Scope أو Model Pilot."/>
    </section>

    <section className="section-block">
      <SectionHeading eyebrow="المساعدون" title="الأدوار المتاحة للاختيار البشري" detail="بطاقات عملية بدل سجل تقني. كل مخرج لاحق يبقى مقترحًا للمراجعة." link={{ href: "/agent-console/tools", label: "عرض الكل" }}/>
      <AgentShowcase limit={4}/>
    </section>

    <section className="section-block split-readiness">
      <StateGate state={workspaces} label="مساحات العمل">{(data) => <WorkspaceSummary data={data}/>}</StateGate>
      <StateGate state={health} label="صحة النظام">{(data) => <HealthSummary data={asRecord(data)}/>}</StateGate>
    </section>
  </Layout>;
}

function WorkspaceSummary({ data }: { data: CollectionResponse }) {
  const items = asItems(data).slice(0, 3);
  return <article className="operational-card"><SectionHeading eyebrow="السياق" title="مساحات عمل جاهزة للعرض" detail="لا اختيار تلقائي ولا تبديل سياق." />
    <div className="stack-list">{items.map((item, index) => <div className="stack-row" key={`${itemLabel(item,index)}-${index}`}><Icon name="workspace" size={18}/><span><strong>{itemLabel(item,index)}</strong><small>{text(item.policy_pack_id, "سياسة غير منشورة")}</small></span><Badge tone="green">{safeStatus(item.lifecycle_state, "DECLARED")}</Badge></div>)}{items.length === 0 && <p className="muted">لا توجد مساحات منشورة.</p>}</div>
  </article>;
}

function HealthSummary({ data }: { data: UnknownRecord }) {
  return <article className="operational-card"><SectionHeading eyebrow="السلامة" title="حدود التشغيل الحالية" detail="قراءة من /health فقط." />
    <div className="safety-stack"><div><span>Agent execution</span><b>{data.agent_execution_enabled === true ? "مفعل" : "محجوب"}</b></div><div><span>Database access</span><b>{data.database_access_enabled === true ? "مفعل" : "غير مفعل"}</b></div><div><span>Platform mutation</span><b>{data.platform_mutation_enabled === true ? "مفعل" : "محجوب"}</b></div></div>
  </article>;
}

function Workspaces() {
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  const governed = useRead<CollectionResponse>("/api/v1/governed-operations/workspaces");
  return <Layout eyebrow="السياق والسياسات" title="مساحات العمل">
    <section className="page-intro"><span className="intro-icon"><Icon name="workspace" size={24}/></span><div><p>اختيار السياق أولًا</p><h2>كل مهمة يجب أن ترتبط بمساحة عمل قبل أي تشغيل لاحق</h2><span>الواجهة تعرض المساحات وتشرح السياسات دون تبديل فعلي أو حفظ اختيار.</span></div></section>
    <StateGate state={workspaces} label="سجل المساحات">{(data) => <WorkspaceCards data={data}/>}</StateGate>
    <section className="section-block compact-top"><SectionHeading eyebrow="التحقق المتقاطع" title="الحالة التشغيلية المحكومة" detail="عرض مقارنة فقط؛ ليس زر تهيئة أو تفعيل."/><StateGate state={governed} label="الحالة المحكومة">{(data) => <GovernedStrip data={data}/>}</StateGate></section>
    <BoundaryPanel title="مسارات التخزين غير معروضة" detail="تعرض الواجهة هوية المساحة والسياسة والحالة فقط؛ المسارات المحلية والـhashes لا تصل إلى نموذج القراءة في المتصفح."/>
  </Layout>;
}

function WorkspaceCards({ data }: { data: CollectionResponse }) {
  const items = asItems(data);
  return <section className="workspace-grid large">{items.map((item, index) => <article className="workspace-card detailed" key={`${itemLabel(item,index)}-${index}`}><div className="workspace-icon"><Icon name="workspace" size={21}/></div><div><p>{text(item.classification, "غير مصنف")}</p><strong>{itemLabel(item, index)}</strong><span>حزمة السياسة: {text(item.policy_pack_id)}</span></div><b>{safeStatus(item.lifecycle_state, "DECLARED")}</b><small>عرض معلومات فقط — لا تبديل سياق</small></article>)}{items.length === 0 && <article className="empty-card">لا توجد مساحات منشورة ضمن عقد القراءة الحالي.</article>}</section>;
}

function GovernedStrip({ data }: { data: CollectionResponse }) {
  const items = asItems(data);
  return <div className="governed-strip">{items.length === 0 ? <span>لا توجد حالة تشغيلية منشورة.</span> : items.map((item,index) => <article key={`${itemLabel(item,index)}-${index}`}><strong>{itemLabel(item,index)}</strong><span>{text(item.policy_pack_id)}</span><b>{safeStatus(item.lifecycle_state, "DECLARED")}</b></article>)}</div>;
}


function TaskDraftReviewFlowPanel({ drafts }: { drafts: TaskDraft[] }) {
  const counts = useMemo(() => ({
    draft: drafts.filter((draft) => draft.status === "draft").length,
    ready: drafts.filter((draft) => draft.status === "ready_for_review").length,
    accepted: drafts.filter((draft) => draft.status === "accepted_as_plan").length,
    returned: drafts.filter((draft) => draft.status === "returned").length,
  }), [drafts]);
  return <section className="section-block review-flow-block">
    <SectionHeading eyebrow="Review Flow" title="دورة مراجعة المسودة — Prepare-only" detail="هذه الدورة تنظّم القرار البشري على المسودة فقط. قبول الخطة لا يعني Apply ولا تشغيل نموذج."/>
    <div className="review-flow-grid">
      <article><span>01</span><strong>Draft</strong><p>مسودة محضّرة عبر Backend أو fallback محلي.</p><b>{counts.draft}</b></article>
      <article><span>02</span><strong>Ready for Review</strong><p>مرسلة للمراجعة البشرية، دون تنفيذ.</p><b>{counts.ready}</b></article>
      <article><span>03</span><strong>Returned</strong><p>تحتاج تعديل نطاق أو صياغة.</p><b>{counts.returned}</b></article>
      <article><span>04</span><strong>Accepted as Plan</strong><p>خطة مقبولة فقط، وليست تفويض Apply.</p><b>{counts.accepted}</b></article>
    </div>
  </section>;
}

function Tasks() {
  const tasks = useRead<CollectionResponse>("/api/v1/local-agents/tasks");
  const governedTasks = useRead<CollectionResponse>(`/api/v1/governed-operations/workspaces/${DEFAULT_WORKSPACE}/tasks`);
  const draftStore = useTaskDrafts();
  const [agentId, setAgentId] = useState(ASSISTANT_CATALOG[0].id);
  const selectedAgent = getAgentById(agentId);
  const handleBackendDraft = async (agent: CatalogAgent, title: string, description: string) => {
    const outcome = await prepareDraftWithBackend(agent, title, description);
    draftStore.addDraft(outcome.draft);
  };
  return <Layout eyebrow="إنشاء وقراءة" title="المهام">
    <section className="page-intro"><span className="intro-icon"><Icon name="task" size={24}/></span><div><p>مسودة قبل التنفيذ</p><h2>هذه الصفحة تجمع المسودات المحلية والمهام المقروءة فقط</h2><span>المسودة تتحضر عبر Backend prepare عند توفره، ثم تعرض محليًا فقط. لا حفظ دائم، لا تنفيذ، لا Model، لا Pilot.</span></div></section>
    <TaskLifecyclePanel />
    <TaskDraftReviewFlowPanel drafts={draftStore.drafts} />
    <ProjectStateManagerPanel compact />
    <GoalToPlanToolSelectionPanel compact />
    <section id="local-drafts" className="section-block"><SectionHeading eyebrow="Backend Prepare + Local View" title="مسودات المهام المحضّرة" detail="مسودات محضّرة بعقد Backend prepare عند توفره، ومعروضة محليًا للمراجعة دون حفظ دائم أو تنفيذ."/><LocalDraftsPanel drafts={draftStore.drafts} onClear={draftStore.clearDrafts} onTransition={draftStore.transitionDraft}/></section>
    <section className="content-grid primary-grid">
      <TaskComposerMock agent={selectedAgent} onPrepareDraft={handleBackendDraft}/>
      <article className="selected-agent-panel">
        <SectionHeading eyebrow="إنشاء سريع" title="اختر مساعدًا لمسودة جديدة" detail="الاختيار يرسل Prepare فقط إلى Backend إذا كان متاحًا، ولا يفتح تنفيذًا."/>
        <div className="agent-select-list">{ASSISTANT_CATALOG.slice(0, 8).map((agent) => <button key={agent.id} type="button" className={agent.id === agentId ? "active" : ""} onClick={() => setAgentId(agent.id)}><Icon name={agent.icon} size={15}/>{agent.name}</button>)}</div>
      </article>
    </section>
    <section className="section-block"><SectionHeading eyebrow="السجل المقروء" title="المهام المتاحة حاليًا" detail="مصدر Command Center القديم للقراءة."/><StateGate state={tasks} label="سجل المهام">{(data) => <CollectionReadPanel data={data} label="سجل المهام" empty="لا توجد مهام منشورة ضمن نموذج القراءة الحالي." detailKeys={["title", "description", "requested_agent", "queue"]} icon="task"/>}</StateGate></section>
    <section className="section-block"><SectionHeading eyebrow="Governed Operations" title="مهام مساحة العمل الافتراضية" detail={`قراءة من ${DEFAULT_WORKSPACE} فقط.`}/><StateGate state={governedTasks} label="المهام المحكومة">{(data) => <CollectionReadPanel data={data} label="المهام المحكومة" empty="لا توجد مهام محكومة في هذه المساحة." detailKeys={["title", "description", "requested_agent", "workspace_id"]} icon="shield"/>}</StateGate></section>
    <BoundaryPanel title="Backend prepare ليس تنفيذًا" detail="العقد الخادمي يعيد draft envelope فقط. persistence=none وexecution_authority=none؛ أي حفظ دائم أو تشغيل يحتاج تفويضًا مستقلًا."/>
  </Layout>;
}

function LocalDraftsPanel({ drafts, onClear, onTransition }: { drafts: TaskDraft[]; onClear: () => void; onTransition: (draftId: string, status: TaskDraftStatus, reviewNote?: string) => void }) {
  if (drafts.length === 0) return <article className="empty-card">لا توجد مسودات بعد. افتح صفحة المساعدين واضغط “تحضير مسودة عبر Backend”.</article>;
  return <div className="local-draft-list">
    <div className="local-draft-controls"><span>{drafts.length} مسودة معروضة محليًا</span><button type="button" onClick={onClear}>مسح عرض المسودات المحلي</button></div>
    {drafts.map((draft) => <article className="local-draft-card" key={draft.id}>
      <div className="local-draft-main"><span className="agent-avatar"><Icon name={getAgentById(draft.agentId).icon} size={20}/></span><div><p>{draft.agentName} — {draft.agentGroup}</p><h3>{draft.title}</h3><span>{draft.description}</span></div></div>
      <div className="local-draft-meta"><Badge tone={taskDraftStatusTone(draft.status)}>{TASK_DRAFT_STATUS_LABELS[draft.status]}</Badge><Badge tone="gold">Prepare-only</Badge><Badge tone={draft.source === "backend_prepare" ? "blue" : "slate"}>{draft.source === "backend_prepare" ? "Backend prepared" : "Browser fallback"}</Badge><Badge tone="slate">{draft.workspaceId}</Badge></div>
      <p className="draft-review-detail">{TASK_DRAFT_STATUS_DETAILS[draft.status]}</p>
      {draft.reviewNote && <p className="draft-review-note">آخر مراجعة: {draft.reviewNote}</p>}
      <div className="draft-review-actions" aria-label="إجراءات مراجعة المسودة">
        <button type="button" onClick={() => onTransition(draft.id, "ready_for_review", "أرسلت للمراجعة البشرية")}>إرسال للمراجعة</button>
        <button type="button" onClick={() => onTransition(draft.id, "accepted_as_plan", "اعتمدت كخطة فقط — لا تنفيذ")}>اعتماد كخطة</button>
        <button type="button" onClick={() => onTransition(draft.id, "returned", "أعيدت للصياغة أو توضيح النطاق")}>إرجاع للصياغة</button>
      </div>
      <div className="tool-chip-row wide">{draft.tools.map((toolId) => <span key={toolId}>{getToolById(toolId)?.name ?? toolId}</span>)}</div>
      {draft.backendDraftId && <div className="backend-draft-status"><span>Backend draft_id</span><b>{draft.backendDraftId}</b><em>persistence={draft.backendPersistence ?? "none"}</em></div>}
      {draft.backendError && <div className="backend-draft-status warning"><span>Fallback reason</span><b>{draft.backendError}</b></div>}
      <small>عرض محلي: {new Date(draft.createdAt).toLocaleString("ar")}</small>
    </article>)}
  </div>;
}

function Reviews() {
  const reviews = useRead<CollectionResponse>("/api/v1/local-agents/reviews");
  const governedReviews = useRead<CollectionResponse>(`/api/v1/governed-operations/workspaces/${DEFAULT_WORKSPACE}/reviews`);
  return <Layout eyebrow="قرار بشري" title="المراجعات">
    <section className="page-intro"><span className="intro-icon"><Icon name="review" size={24}/></span><div><p>مركز قرار لا مركز تنفيذ</p><h2>المراجعة البشرية تفصل المقترح عن التطبيق</h2><span>لا يظهر اسم المراجع أو موقع الملف أو بيانات الأرشيف داخل نموذج القراءة العام.</span></div></section>
    <section className="section-block"><SectionHeading eyebrow="سجل عام" title="المراجعات المنشورة"/><StateGate state={reviews} label="سجل المراجعات">{(data) => <CollectionReadPanel data={data} label="سجل المراجعات" empty="لا توجد مراجعات منشورة ضمن نموذج القراءة الحالي." detailKeys={["decision", "scope", "transition_status", "record_type"]} statusKey="decision" icon="review"/>}</StateGate></section>
    <section className="section-block"><SectionHeading eyebrow="مساحة العمل" title="مراجعات مساحة العمل الافتراضية"/><StateGate state={governedReviews} label="المراجعات المحكومة">{(data) => <CollectionReadPanel data={data} label="المراجعات المحكومة" empty="لا توجد مراجعات محكومة في هذه المساحة." detailKeys={["decision", "task_id", "reason", "reviewer"]} statusKey="decision" icon="shield"/>}</StateGate></section>
    <BoundaryPanel title="لا قرار من الواجهة" detail="هذه الصفحة تعرض المراجعات الحالية فقط، ولا تتيح قبولًا أو رفضًا أو تعديلًا أو إعادة تعيين."/>
  </Layout>;
}

function Evidence() {
  const evidence = useRead<CollectionResponse>("/api/v1/local-agents/evidence");
  const governedEvidence = useRead<CollectionResponse>(`/api/v1/governed-operations/workspaces/${DEFAULT_WORKSPACE}/evidence`);
  return <Layout eyebrow="السجل والمراجع" title="الأدلة التشغيلية">
    <section className="page-intro"><span className="intro-icon"><Icon name="evidence" size={24}/></span><div><p>أدلة يمكن قراءتها</p><h2>لا تُعرض آثار output أو مسارات الملفات المحلية</h2><span>يقتصر المستعرض على الأدلة المنشورة ضمن نموذج القراءة الآمن؛ لا رفع أو تعديل أو تنزيل ملفات.</span></div></section>
    <section className="section-block"><SectionHeading eyebrow="السجل العام" title="الأدلة المنشورة"/><StateGate state={evidence} label="سجل الأدلة">{(data) => <CollectionReadPanel data={data} label="سجل الأدلة" empty="لا توجد أدلة تشغيلية قانونية منشورة ضمن نموذج القراءة الحالي." detailKeys={["category", "status", "summary", "task_id"]} icon="evidence"/>}</StateGate></section>
    <section className="section-block"><SectionHeading eyebrow="مساحة العمل" title="أدلة مساحة العمل الافتراضية"/><StateGate state={governedEvidence} label="الأدلة المحكومة">{(data) => <CollectionReadPanel data={data} label="الأدلة المحكومة" empty="لا توجد أدلة محكومة في هذه المساحة." detailKeys={["category", "summary", "task_id", "evidence_type"]} icon="shield"/>}</StateGate></section>
    <BoundaryPanel title="الأرشيف المولد ليس سجل تشغيل" detail="يُحجب كل عنصر يقع تحت output أو يحمل مسارًا محليًا أو hash أو metadata أرشيفية من استجابة المتصفح."/>
  </Layout>;
}

function ToolRegistryPanel() {
  const groups: ToolStatus[] = ["approved", "deferred", "blocked"];
  return <div className="tool-registry-grid">
    {groups.map((status) => {
      const tools = LOCAL_TOOL_REGISTRY.filter((tool) => tool.status === status);
      return <section className={`tool-status-column tool-status-${status}`} key={status}>
        <div className="tool-status-head"><Badge tone={statusTone(status)}>{TOOL_STATUS_LABELS[status]}</Badge><strong>{tools.length} أداة</strong><span>{TOOL_STATUS_DETAIL[status]}</span></div>
        {tools.map((tool) => <article className="tool-registry-card" key={tool.id}>
          <div><strong>{tool.name}</strong><p>{tool.purpose}</p></div>
          <span>{tool.category}</span>
          <small>{tool.boundary}</small>
        </article>)}
      </section>;
    })}
  </div>;
}

function Tools() {
  const coreHealth = useRead<UnknownRecord>("/api/v1/local-agent-core/health");
  return <Layout eyebrow="كتالوج المساعدين" title="المساعدون المحليون وبدء المهمة">
    <section className="page-intro"><span className="intro-icon"><Icon name="agent" size={24}/></span><div><p>اختيار مساعد ثم صياغة مهمة</p><h2>واجهة تشغيل أولى: من أحتاج؟ وماذا سينتج؟</h2><span>هذه الصفحة تعرض كتالوج المساعدين وسجل الأدوات وتسمح بإنشاء مسودة محلية فقط. لا POST، لا Shell، لا Git، لا Model Execution.</span></div></section>
    <StateGate state={coreHealth} label="صحة نواة المساعدين">{(data) => <CoreHealthBanner data={asRecord(data)}/>}</StateGate>
    <section className="section-block"><SectionHeading eyebrow="Approved Tools Only" title="سجل الأدوات وحالة كل أداة" detail="الدفعة الحالية تسمح بالأدوات المقبولة فقط. المؤجلة والمرفوضة ظاهرة حتى لا ننساها، لكنها غير مفعلة."/><ToolRegistryPanel /></section>
    <ToolBackendContractPanel />
    <DeferredGatePanel />
    <GoalToPlanToolSelectionPanel compact />
    <AssistantCatalogConsole />
    <BoundaryPanel title="اختيار المساعد ليس تنفيذًا" detail="الزر يجهز تصور المهمة في الشاشة فقط. الربط الحقيقي بإنشاء مسودة خادمية يحتاج دفعة لاحقة وتفويضًا صريحًا."/>
  </Layout>;
}

function CoreHealthBanner({ data }: { data: UnknownRecord }) {
  const posture = asRecord(data.system_posture);
  return <section className="health-banner"><MetricCard icon="agent" label="نمط النواة" value={safeStatus(data.agent_runtime, "READ ONLY")} detail="تعريف خادمي مقروء" tone="blue"/><MetricCard icon="lock" label="تنفيذ النموذج" value={safeStatus(posture.MODEL_EXECUTION ?? data.model_execution, "NONE")} detail="لا تشغيل من المتصفح" tone="red"/><MetricCard icon="shield" label="سلطة المخرج" value={safeStatus(data.agent_output_authority, "PROPOSAL ONLY")} detail="مقترح فقط" tone="gold"/></section>;
}

function PilotControl() {
  const pilot = useRead<UnknownRecord>(`/api/v1/local-agent-core/workspaces/${DEFAULT_WORKSPACE}/model-pilot/status`);
  return <Layout eyebrow="بوابة تجريب مقفلة" title="Pilot">
    <section className="page-intro"><span className="intro-icon"><Icon name="lock" size={24}/></span><div><p>حالة مقروءة فقط</p><h2>لا يبدأ الـPilot من هذه الصفحة</h2><span>تُقرأ الحالة المنشورة دون أي زر تشغيل أو تبديل سياسة.</span></div></section>
    <StateGate state={pilot} label="حالة الـPilot">{(data) => { const record = asRecord(data); return <section className="metrics-grid"><MetricCard icon="lock" label="حالة الـPilot" value={safeStatus(record.pilot_execution, text(record.status, "NOT EXECUTED"))} detail="قراءة من العقد الخادمي" tone="red"/><MetricCard icon="agent" label="تنفيذ النموذج" value={safeStatus(record.model_execution, "NONE")} detail="لا يبدأ من الواجهة" tone="red"/><MetricCard icon="shield" label="بوابة التنفيذ" value={safeStatus(record.execution_gateway, "DISABLED" )} detail="لا تفويض ضمن هذه الشاشة" tone="gold"/><MetricCard icon="workspace" label="مساحة العمل" value="PalWakf Government" detail="مسار حالة مقروء ومقيد" tone="blue"/></section>; }}</StateGate>
    <InitialOperationReadinessPanel compact />
    <LocalModelStrategyMatrixPanel />
    <LocalModelReadinessGatePanel />
    <ProjectRealityCharterPanel compact />
    <ProjectStateManagerPanel compact />
    <section className="blocked-list"><BlockedAction icon="agent" title="بدء Pilot" detail="يتطلب تفويضًا مستقلاً وActor Scope وخطة UAT."/><BlockedAction icon="tool" title="تشغيل نموذج" detail="غير متاح من شاشة React."/><BlockedAction icon="evidence" title="تثبيت نتائج" detail="لا يتم حفظ نتائج أو مخرجات من المتصفح."/></section>
    <BoundaryPanel title="Pilot غير منفذ" detail="هذه الشاشة تقرأ الحالة فقط. أي تشغيل مستقبلي يحتاج تفويضًا مستقلاً وActor Scope واختبار قبول موثق."/>
  </Layout>;
}

function ProjectReaderSummaryPanel({ data }: { data: UnknownRecord }) {
  const counts = asRecord(data.counts);
  const roots = recordArray(counts.roots);
  const keyFiles = recordArray(data.key_files);
  const routes = recordArray(data.route_matrix).slice(0, 18);
  const guardrails = asRecord(data.guardrails);
  return <>
    <section className="metrics-grid project-reader-metrics">
      <MetricCard icon="project" label="ملفات مقروءة" value={displayNumber(counts.total_files)} detail="ضمن الجذور المسموحة فقط" tone="blue"/>
      <MetricCard icon="workspace" label="الحجم التقريبي" value={`${displayNumber(counts.total_size_bytes)} bytes`} detail="Metadata فقط" tone="slate"/>
      <MetricCard icon="shield" label="النمط" value={safeStatus(data.mode, "READ ONLY")} detail="Workspace-scoped" tone="gold"/>
      <MetricCard icon="lock" label="Shell / Git / Model" value="محجوب" detail="لا تنفيذ ولا أوامر" tone="red"/>
    </section>
    <section className="content-grid primary-grid">
      <article className="reader-panel">
        <SectionHeading eyebrow="Allowed roots" title="الجذور التي تمت قراءتها" detail="هذه إحصاءات ملفات فقط، وليست قراءة محتوى كامل."/>
        <div className="reader-list">
          {roots.map((root) => <div className="reader-row" key={text(root.root)}><strong>{text(root.root)}</strong><span>{root.exists === true ? "موجود" : "غير موجود"}</span><b>{displayNumber(root.file_count)} ملف</b></div>)}
        </div>
      </article>
      <article className="reader-panel">
        <SectionHeading eyebrow="Guardrails" title="حدود الأداة" detail="نجاح القراءة لا يمنح أي صلاحية تنفيذ."/>
        <div className="reader-list compact">
          {Object.entries(guardrails).slice(0, 10).map(([key, value]) => <div className="reader-row" key={key}><strong>{key}</strong><span>{String(value)}</span></div>)}
        </div>
      </article>
    </section>
    <section className="section-block">
      <SectionHeading eyebrow="Key files" title="ملفات رئيسية وحالتها" detail="يعرض وجود الملفات وhash عند توفرها، دون فتح محتواها."/>
      <div className="reader-table">
        {keyFiles.map((file) => <article className="reader-file-card" key={text(file.path)}><strong>{text(file.path)}</strong><span>{file.exists === true ? "موجود" : "غير موجود"}</span><small>{typeof file.sha256 === "string" ? `SHA256: ${file.sha256.slice(0, 16)}...` : "لا hash"}</small></article>)}
      </div>
    </section>
    <section className="section-block">
      <SectionHeading eyebrow="Route matrix" title="مصفوفة المسارات المقروءة" detail="أول 18 سطرًا دالًا من ملفات Router وواجهة React."/>
      <div className="route-matrix-list">
        {routes.map((route, index) => <article className="route-matrix-row" key={`${text(route.file)}-${text(route.line)}-${index}`}><b>{text(route.file)}</b><span>سطر {text(route.line)}</span><code>{text(route.text)}</code></article>)}
        {routes.length === 0 && <article className="empty-card">لا توجد مسارات مقروءة ضمن النطاق.</article>}
      </div>
    </section>
  </>;
}

function Projects() {
  const projectReader = useRead<UnknownRecord>(`/api/v1/project-reader/workspaces/${DEFAULT_WORKSPACE}/summary`);
  const projectReaderHealth = useRead<UnknownRecord>("/api/v1/project-reader/health");
  return <Layout eyebrow="أداة قراءة فعلية" title="قارئ المشروع المحلي">
    <section className="page-intro project-reader-intro"><span className="intro-icon"><Icon name="project" size={24}/></span><div><p>LOCAL_PROJECT_READER_TOOL_V1</p><h2>قراءة بنية المشروع دون تنفيذ أو تعديل</h2><span>هذه أول أداة فعلية مقبولة بعد بوابة إعادة التقييم: GET-only، داخل workspace، بلا Shell، بلا Git، بلا Model، بلا DB write.</span></div></section>
    <StateGate state={projectReaderHealth} label="صحة قارئ المشروع">{(data) => <section className="health-banner"><MetricCard icon="pulse" label="الخدمة" value={text(asRecord(data).service, "project-reader")} detail="GET-only" tone="blue"/><MetricCard icon="shield" label="الحالة" value={safeStatus(asRecord(data).status, "READY")} detail="أداة مقبولة الآن" tone="gold"/><MetricCard icon="lock" label="الصلاحية" value="READ ONLY" detail="لا تنفيذ" tone="red"/></section>}</StateGate>
    <StateGate state={projectReader} label="ملخص قراءة المشروع">{(data) => <ProjectReaderSummaryPanel data={asRecord(data)}/>}</StateGate>
    <CodebaseUnderstandingReadModelPanel />
    <CodebaseUnderstandingRoadmapPanel />
    <LocalModelStrategyMatrixPanel />
    <GoalToPlanToolSelectionPanel compact />
    <ProjectRealityCharterPanel compact />
    <ProjectStateManagerPanel compact />
    <InitialOperationReadinessPanel compact />
    <BackendAlignmentGuidePanel />
    <BoundaryPanel title="قارئ المشروع ليس منفذًا" detail="الأداة لا تشغل أوامر نظام، لا تستخدم Git، لا تفتح الشبكة، ولا تعدل أي ملف. هي تقرأ metadata ومسارات فقط لتمكين المهام التالية بأمان."/>
  </Layout>;
}

function Diagnostics() {
  const health = useRead<UnknownRecord>("/health");
  const commandHealth = useRead<UnknownRecord>("/api/v1/local-agents/system-health");
  const coreHealth = useRead<UnknownRecord>("/api/v1/local-agent-core/health");
  const opsHealth = useRead<UnknownRecord>("/api/v1/governed-operations/health");
  const workspaceHealth = useRead<UnknownRecord>("/api/v1/workspaces/health");
  const rows = useMemo(() => [
    ["Application", health],
    ["Command Center", commandHealth],
    ["Local Agent Core", coreHealth],
    ["Governed Operations", opsHealth],
    ["Workspace Core", workspaceHealth],
  ] as const, [health, commandHealth, coreHealth, opsHealth, workspaceHealth]);
  return <Layout eyebrow="سلامة النظام" title="التشخيص الصحي">
    <section className="page-intro"><span className="intro-icon"><Icon name="pulse" size={24}/></span><div><p>قراءة حالة الخدمة</p><h2>فحص شفاف بلا تغيير إعدادات</h2><span>تعرض هذه الصفحة العقود الصحية المتاحة؛ لا تبدأ خدمة ولا تعيد تشغيل أي مكوّن.</span></div></section>
    <StateGate state={health} label="الحالة الصحية العامة">{(data) => { const record = asRecord(data); return <div className="diagnostic-grid"><MetricCard icon="pulse" label="الخدمة" value={text(record.service)} detail={`نطاق الربط: ${text(record.bind_scope)}`} tone="blue"/><MetricCard icon="shield" label="التحقق الآمن" value={record.safety_ok === true ? "سليم" : "يتطلب مراجعة"} detail="قيمة مقروءة من /health" tone={record.safety_ok === true ? "gold" : "red"}/><MetricCard icon="agent" label="تنفيذ المساعد" value={record.agent_execution_enabled === true ? "مفعل" : "محجوب"} detail="لا تغيّر هذه الشاشة الوضع" tone="red"/><MetricCard icon="lock" label="وصول قاعدة البيانات" value={record.database_access_enabled === true ? "مفعل" : "غير مفعل"} detail="عرض حالة فقط" tone="slate"/></div>; }}</StateGate>
    <BackendAlignmentGuidePanel />
    <CodebaseUnderstandingReadModelPanel />
    <LocalModelStrategyMatrixPanel />
    <LocalModelReadinessGatePanel />
    <GoalToPlanToolSelectionPanel compact />
    <ProjectRealityCharterPanel compact />
    <ProjectStateManagerPanel compact />
    <section className="section-block"><SectionHeading eyebrow="العقود الفرعية" title="حالة وحدات القراءة" detail="كل صف هو GET فقط."/><div className="service-list">{rows.map(([label, state]) => <ServiceRow key={label} label={label} state={state}/>)}</div></section>
    <BoundaryPanel title="الصحة ليست تفويضًا" detail="نجاح التشخيص لا يفتح Model أو Pilot أو كتابة أو نشر. لكل انتقال بوابة تفويض مستقلة ودليل قبول منفصل."/>
  </Layout>;
}

function ServiceRow({ label, state }: { label: string; state: ReadState<UnknownRecord> }) {
  const status = state.kind === "ready" ? "PASS" : state.kind === "loading" ? "READING" : state.kind.toUpperCase();
  return <article className="service-row"><Icon name={state.kind === "ready" ? "shield" : "pulse"} size={18}/><strong>{label}</strong><span>{state.kind === "ready" ? text(asRecord(state.data).service ?? asRecord(state.data).module ?? asRecord(state.data).status, "READY") : state.kind === "error" ? state.detail : state.kind}</span><Badge tone={state.kind === "ready" ? "green" : state.kind === "error" ? "red" : "slate"}>{status}</Badge></article>;
}



type ReadinessStatus = "ready" | "partial" | "blocked" | "future";
type CapabilityMode = "accepted" | "read_only" | "prepare_only" | "future_gate" | "blocked";

type InitialReadinessItem = {
  id: string;
  title: string;
  status: ReadinessStatus;
  owner: string;
  evidence: string;
  next: string;
};

type BlockedCapabilityDecision = {
  id: string;
  capability: string;
  priorState: string;
  decision: string;
  allowedMode: CapabilityMode;
  reason: string;
  nextGate: string;
};

const INITIAL_OPERATION_READINESS_ITEMS: InitialReadinessItem[] = [
  { id: "ui", title: "واجهة تشغيل يومية", status: "ready", owner: "Frontend", evidence: "Operational UX accepted: هدف → خطة → مسودة → مراجعة", next: "استخدامها كمسار التشغيل الأولي." },
  { id: "goal", title: "Goal Planner Productized", status: "ready", owner: "Frontend", evidence: "قوالب أهداف وخطة deterministic ومسودات من الخطة", next: "اختبار هدف جديد وتحضير مسودات." },
  { id: "task", title: "Task Draft + Review Flow", status: "ready", owner: "Frontend/Backend contract", evidence: "Backend prepare + Review status accepted", next: "تثبيت أول سيناريو فحص." },
  { id: "project_reader", title: "Project Reader", status: "ready", owner: "Backend GET-only", evidence: "قارئ المشروع مقبول read-only", next: "استخدامه كمدخل لفهم المشروع قبل أي تنفيذ." },
  { id: "state", title: "Project State Model", status: "partial", owner: "Design/UI", evidence: "State Manager design accepted", next: "يحتاج تخزين محكوم لاحقًا إذا أردنا الاستئناف الحقيقي." },
  { id: "models", title: "Local Model Runtime", status: "future", owner: "Model gate", evidence: "Strategy matrix accepted only", next: "فتح Runtime Readiness Gate لاحقًا، لا تشغيل الآن." },
  { id: "execution", title: "Execution Layer", status: "blocked", owner: "Governance", evidence: "No Shell/Git/Code execution/self-apply", next: "يبقى محجوبًا حتى بوابات مستقلة." },
];

const BLOCKED_CAPABILITY_REASSESSMENT: BlockedCapabilityDecision[] = [
  { id: "model", capability: "Model execution", priorState: "محجوب", decision: "لا يفتح الآن", allowedMode: "future_gate", reason: "نحتاج Local Model Runtime Readiness قبل أي invoke.", nextGate: "LOCAL_MODEL_RUNTIME_READINESS_GATE_V1" },
  { id: "pilot", capability: "Pilot execution", priorState: "محجوب", decision: "لا يفتح الآن", allowedMode: "future_gate", reason: "الـPilot يحتاج actor scope وخطة UAT وسجل إيقاف.", nextGate: "CONTROLLED_LOCAL_MODEL_PILOT_GATE_V1" },
  { id: "shell", capability: "Shell", priorState: "محجوب", decision: "يبقى محجوبًا", allowedMode: "blocked", reason: "خطر mutation وتشغيل أوامر خارجية؛ ليس لازمًا للتشغيل الأولي.", nextGate: "SANDBOXED_COMMAND_GATE_V1 لاحقًا فقط" },
  { id: "git", capability: "Git operations", priorState: "محجوب", decision: "يبقى محجوبًا", allowedMode: "blocked", reason: "قد يغير history أو يلامس remote؛ لا حاجة الآن.", nextGate: "GIT_READONLY_STATUS_GATE_V1 كخطوة مستقبلية" },
  { id: "code", capability: "Code execution", priorState: "محجوب", decision: "يبقى محجوبًا", allowedMode: "blocked", reason: "يتطلب sandbox وسياسة موارد ومخرجات قابلة للتدقيق.", nextGate: "LOCAL_CODE_SANDBOX_DESIGN_GATE_V1" },
  { id: "db", capability: "DB persistence", priorState: "محجوب", decision: "مؤجل إلى SQLite محكوم", allowedMode: "future_gate", reason: "نحتاج حفظ مسودات وحالة مشروع لاحقًا، لكن ليس ضمن التشغيل الأولي الحالي.", nextGate: "LOCAL_TASK_STORE_SQLITE_GOVERNED_PERSISTENCE_V1" },
  { id: "web", capability: "Web search", priorState: "محجوب", decision: "يبقى محجوبًا", allowedMode: "blocked", reason: "يفتح سطح شبكة ومصادر خارجية؛ غير لازم للفحص الأولي.", nextGate: "LOCAL_SEARCH_READINESS_GATE_V1 لاحقًا" },
  { id: "self_apply", capability: "Self-apply / autonomous build", priorState: "محجوب", decision: "يبقى محجوبًا", allowedMode: "blocked", reason: "يتعارض مع Human Authority وNo Hidden Execution قبل نظام أدلة وتنفيذ محكوم.", nextGate: "NEVER_DIRECT; requires multiple future gates" },
  { id: "reader", capability: "Project Reader", priorState: "كان مؤجلًا", decision: "مقبول", allowedMode: "read_only", reason: "GET-only وworkspace-scoped ويخدم التشغيل الأولي.", nextGate: "مقبول حاليًا" },
  { id: "draft_prepare", capability: "Task draft prepare", priorState: "كان localStorage فقط", decision: "مقبول", allowedMode: "prepare_only", reason: "يعيد envelope بدون persistence وبدون execution.", nextGate: "مقبول حاليًا" },
];

const FIRST_RUN_TEST_PLAN = [
  "فتح /agent-console والتأكد أن المسار اليومي واضح.",
  "فتح /agent-console/goal-planner واختيار قالب هدف.",
  "تحضير مسودات من الخطة ثم فتح /agent-console/tasks.",
  "إرسال مسودة للمراجعة ثم قبولها كخطة في /agent-console/reviews.",
  "فتح /agent-console/projects والتأكد من قراءة Project Reader فقط.",
  "فتح /agent-console/initial-operation والتأكد من Matrix المحجوبات.",
  "اختبار سلبي: لا يوجد زر Model/Pilot/Shell/Git/Build/Self-Apply.",
];

const INITIAL_OPERATION_STOP_RULES = [
  "ظهور زر تنفيذ فعلي غير مصرح به.",
  "أي محاولة تشغيل Model/Pilot من الواجهة.",
  "أي طلب Shell/Git/Code execution من صفحة تشغيلية.",
  "أي حفظ دائم غير مصرح به خارج localStorage المؤقت.",
  "عودة صفحات التشغيل إلى ازدحام حوكمي يعيق المستخدم.",
];

function readinessTone(status: ReadinessStatus): "green" | "blue" | "gold" | "red" | "slate" {
  if (status === "ready") return "green";
  if (status === "partial") return "gold";
  if (status === "future") return "blue";
  return "red";
}

function capabilityTone(mode: CapabilityMode): "green" | "blue" | "gold" | "red" | "slate" {
  if (mode === "accepted") return "green";
  if (mode === "read_only") return "blue";
  if (mode === "prepare_only") return "gold";
  if (mode === "future_gate") return "slate";
  return "red";
}

function InitialOperationReadinessPanel({ compact = false }: { compact?: boolean }) {
  const readyCount = INITIAL_OPERATION_READINESS_ITEMS.filter((item) => item.status === "ready").length;
  const futureCount = BLOCKED_CAPABILITY_REASSESSMENT.filter((item) => item.allowedMode === "future_gate").length;
  const blockedCount = BLOCKED_CAPABILITY_REASSESSMENT.filter((item) => item.allowedMode === "blocked").length;
  return <section className={compact ? "initial-readiness compact" : "section-block initial-readiness"}>
    {!compact && <SectionHeading eyebrow="Initial Operation" title="جاهزية التشغيل الأولي" detail="هذه ليست بوابة تنفيذ؛ إنها خريطة ما هو جاهز وما يبقى محجوبًا قبل أول فحص تشغيل."/>}
    <div className="initial-readiness-metrics">
      <MetricCard icon="review" label="جاهز الآن" value={String(readyCount)} detail="عناصر تشغيل مقبولة" tone="gold"/>
      <MetricCard icon="shield" label="بوابات لاحقة" value={String(futureCount)} detail="تحتاج تفويضًا مستقلًا" tone="gold"/>
      <MetricCard icon="lock" label="يبقى محجوبًا" value={String(blockedCount)} detail="غير لازم للتشغيل الأولي" tone="red"/>
    </div>
  </section>;
}

function InitialOperationReadinessPage() {
  return <Layout eyebrow="تشغيل أولي" title="جاهزية التشغيل الأولي وإعادة تقييم المحجوبات">
    <section className="ux-hero readiness-hero">
      <div>
        <p>Initial Operation Readiness</p>
        <h2>نجهز أول تشغيل وفحص دون فتح التنفيذ العشوائي</h2>
        <span>هذه الصفحة تجمع ما أصبح مقبولًا، ما يحتاج فحصًا أوليًا، وما يبقى محجوبًا إلى بوابات لاحقة. الهدف الآن: تشغيل أولي قابل للفحص، لا تشغيل نماذج ولا بناء ذاتي.</span>
        <div className="ux-hero-actions"><a href="/agent-console/goal-planner">ابدأ سيناريو فحص</a><a href="/agent-console/tasks">عرض المسودات</a></div>
      </div>
      <aside>
        <strong>نمط المرحلة</strong>
        <small>Full-stack staged readiness</small>
        <b>0</b>
        <span>تنفيذ فعلي مصرح به الآن</span>
      </aside>
    </section>
    <InitialOperationReadinessPanel />
    <section className="section-block readiness-checklist"><SectionHeading eyebrow="Readiness Plan" title="ما الجاهز للتشغيل الأولي؟" detail="الجاهزية هنا تعني فحصًا تشغيليًا محدودًا: UI + Backend contracts + Project Reader + Draft/Review."/>
      <div className="readiness-card-grid">
        {INITIAL_OPERATION_READINESS_ITEMS.map((item) => <article key={item.id} className={`readiness-card status-${item.status}`}>
          <div><Icon name={item.status === "blocked" ? "lock" : item.status === "ready" ? "review" : "pulse"} size={20}/><Badge tone={readinessTone(item.status)}>{item.status}</Badge></div>
          <strong>{item.title}</strong><p>{item.evidence}</p><small>Owner: {item.owner}</small><span>{item.next}</span>
        </article>)}
      </div>
    </section>
    <section className="section-block capability-matrix"><SectionHeading eyebrow="Blocked Capability Reassessment" title="إعادة تقييم المحجوبات" detail="القرار ليس فتح كل شيء، بل تحديد ما يمكن فحصه الآن وما يحتاج بوابة مستقلة."/>
      <div className="capability-table">
        {BLOCKED_CAPABILITY_REASSESSMENT.map((item) => <article key={item.id} className={`capability-row mode-${item.allowedMode}`}>
          <div><strong>{item.capability}</strong><span>الحالة السابقة: {item.priorState}</span></div>
          <p>{item.reason}</p>
          <Badge tone={capabilityTone(item.allowedMode)}>{item.allowedMode}</Badge>
          <small>{item.decision}</small><code>{item.nextGate}</code>
        </article>)}
      </div>
    </section>
    <section className="content-grid primary-grid">
      <article className="reader-panel"><SectionHeading eyebrow="First Run Test Plan" title="خطة الفحص الأولي" detail="اختبار يدوي قصير يغطي المسار المقبول دون فتح المحجوبات."/><div className="reader-list compact">{FIRST_RUN_TEST_PLAN.map((item, index) => <div className="reader-row" key={item}><strong>{String(index + 1).padStart(2, "0")}</strong><span>{item}</span></div>)}</div></article>
      <article className="reader-panel"><SectionHeading eyebrow="Stop Rules" title="قواعد الإيقاف" detail="أي ظهور لهذه المؤشرات يوقف التشغيل الأولي ويعيدنا إلى إصلاح ضيق."/><div className="reader-list compact">{INITIAL_OPERATION_STOP_RULES.map((item, index) => <div className="reader-row" key={item}><strong>STOP {index + 1}</strong><span>{item}</span></div>)}</div></article>
    </section>
    <BoundaryPanel title="جاهزية التشغيل ليست تفويض تنفيذ" detail="هذه الدفعة لا تفتح Model أو Pilot أو Shell أو Git أو Code execution أو DB persistence أو self-apply. كل قدرة حساسة تحتاج تفويضًا وبوابة مستقلة."/>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

type OperationalCard = {
  id: string;
  title: string;
  detail: string;
  href: string;
  icon: IconName;
  tone: "green" | "blue" | "gold" | "red" | "slate";
};

const OPERATIONAL_NEXT_ACTIONS: OperationalCard[] = [
  { id: "goal", title: "ابدأ بهدف جديد", detail: "اكتب هدفًا كبيرًا ليظهر كنطاق وخطة وأدوات مقترحة، دون تنفيذ.", href: "/agent-console/goal-planner", icon: "task", tone: "green" },
  { id: "initial", title: "جاهزية التشغيل الأولي", detail: "افحص ما أصبح جاهزًا وما يبقى محجوبًا قبل أول تشغيل.", href: "/agent-console/initial-operation", icon: "pulse", tone: "gold" },
  { id: "draft", title: "حضّر مسودة مهمة", detail: "اختر مساعدًا وأنشئ Draft عبر Backend prepare مع بقاء persistence=none.", href: "/agent-console/tasks", icon: "agent", tone: "blue" },
  { id: "project", title: "اقرأ بنية المشروع", detail: "افتح خريطة المشروع والمسارات والملفات الرئيسية بصيغة قراءة آمنة.", href: "/agent-console/projects", icon: "project", tone: "gold" },
  { id: "domains", title: "مجالات التخصص", detail: "اعرف الوكلاء والمجالات التي سيدعمها المشروع لاحقًا: Flutter، React، Supabase، GIS، مستندات وترجمة.", href: "/agent-console/domain-capabilities", icon: "agent", tone: "blue" },
  { id: "tools", title: "اختر المساعد المناسب", detail: "استعرض المساعدين والأدوات المقبولة الآن دون إغراق حوكمي.", href: "/agent-console/tools", icon: "tool", tone: "slate" },
];

const OPERATIONAL_FLOW_STEPS = [
  { id: "01", title: "هدف", detail: "ماذا تريد بناءه أو فهمه؟" },
  { id: "02", title: "خطة", detail: "نطاق وخطوات وأدوات مقترحة." },
  { id: "03", title: "مسودة", detail: "Task Draft قابل للمراجعة." },
  { id: "04", title: "مراجعة", detail: "Accepted as Plan فقط، لا تنفيذ." },
];

function OperationalGovernanceLinks({ compact = false }: { compact?: boolean }) {
  const links: OperationalCard[] = [
    { id: "charter", title: "الميثاق", detail: "الحقيقة الرسمية والحدود السيادية.", href: "/agent-console/charter", icon: "shield", tone: "gold" },
    { id: "state", title: "حالة المشروع", detail: "Goal/Plan/Review/Boundary كنموذج حالة.", href: "/agent-console/state-manager", icon: "project", tone: "blue" },
    { id: "diagnostics", title: "التشخيص", detail: "حالة الخدمات والعقود الصحية.", href: "/agent-console/diagnostics", icon: "pulse", tone: "slate" },
    { id: "pilot", title: "Pilot Control", detail: "كل التشغيل والنماذج ما زالت مقفلة.", href: "/agent-console/pilot-control", icon: "lock", tone: "red" },
  ];
  return <section className={compact ? "ux-subpages compact" : "section-block ux-subpages"}>
    {!compact && <SectionHeading eyebrow="تفاصيل عند الحاجة" title="صفحات الحوكمة والتشخيص" detail="نقلنا التفاصيل الثقيلة إلى صفحات فرعية حتى تبقى صفحات العمل اليومية سهلة ومباشرة."/>}
    <div className="ux-subpage-grid">
      {links.map((link) => <a className={`ux-subpage-card ux-tone-${link.tone}`} href={link.href} key={link.id}>
        <Icon name={link.icon} size={18}/><strong>{link.title}</strong><span>{link.detail}</span>
      </a>)}
    </div>
  </section>;
}

function OperationalActionCards({ items = OPERATIONAL_NEXT_ACTIONS }: { items?: OperationalCard[] }) {
  return <section className="ux-action-grid" aria-label="إجراءات تشغيلية سريعة">
    {items.map((item) => <a className={`ux-action-card ux-tone-${item.tone}`} href={item.href} key={item.id}>
      <span><Icon name={item.icon} size={22}/></span>
      <div><strong>{item.title}</strong><p>{item.detail}</p></div>
      <i>فتح</i>
    </a>)}
  </section>;
}

function OperationalFlowPanel() {
  return <section className="section-block ux-flow-panel">
    <SectionHeading eyebrow="Workflow" title="مسار العمل البسيط" detail="الصفحات الرئيسية تعرض ما يحتاجه المستخدم للعمل اليومي، أما الحدود التفصيلية فموجودة في الصفحات الفرعية."/>
    <div className="ux-flow-steps">
      {OPERATIONAL_FLOW_STEPS.map((step) => <article key={step.id}><span>{step.id}</span><strong>{step.title}</strong><p>{step.detail}</p></article>)}
    </div>
  </section>;
}



type DomainSupportState = "current_prepare" | "design_ready" | "future_gate" | "blocked_runtime";

type SpecializedAgentRole = {
  id: string;
  title: string;
  role: string;
  domains: string[];
  outputs: string;
  runtimeGate: string;
};

type DomainCapability = {
  id: string;
  title: string;
  currentUse: string;
  futureTools: string;
  agents: string[];
  state: DomainSupportState;
  nextGate: string;
};

const SPECIALIZED_AGENT_ROLES: SpecializedAgentRole[] = [
  { id: "orchestrator", title: "وكيل المنسق", role: "يستقبل الهدف ويوزع العمل بين الوكلاء المتخصصين.", domains: ["كل المجالات", "Goal-to-Plan", "Review Gate"], outputs: "خطة توزيع عمل ومراحل مراجعة.", runtimeGate: "Prepare-only حاليًا" },
  { id: "planner", title: "وكيل المخطط", role: "يحوّل الهدف إلى مهام وتبعيات ومخرجات قبول.", domains: ["تحليل متطلبات", "خطة مشروع", "مسودات"], outputs: "Project Plan Draft + Task Drafts.", runtimeGate: "لا Model runtime الآن" },
  { id: "architect", title: "وكيل المعماري", role: "يصمم البنية والتقنيات والحدود قبل كتابة الكود.", domains: ["Full-stack", "Architecture", "DB/API"], outputs: "Architecture brief وقرارات تقنية.", runtimeGate: "Design-only" },
  { id: "frontend", title: "وكيل الواجهة", role: "يدعم React/Next وFlutter/Dart كتخصصات مستقبلية.", domains: ["React", "Next.js", "Flutter", "Dart"], outputs: "تصميم شاشات ومكونات وخطة ربط API.", runtimeGate: "No code execution" },
  { id: "backend", title: "وكيل Backend وقواعد البيانات", role: "يدعم FastAPI وSupabase وSQL كنطاقات تصميم وتشخيص لاحق.", domains: ["Backend APIs", "Supabase", "SQL", "Migrations"], outputs: "API contract وDB design plan.", runtimeGate: "No DB write" },
  { id: "gis", title: "وكيل GIS والخرائط", role: "يجهز لاحقًا مسارات GeoJSON/Shapefile/GeoTIFF والخرائط الجوية.", domains: ["GIS", "Maps", "Aerial imagery", "Coordinates"], outputs: "Capability plan وبيانات إدخال آمنة.", runtimeGate: "No GIS processing runtime" },
  { id: "documents", title: "وكيل المستندات والترجمة", role: "يغطي قراءة PDF/Word/صور وOCR والترجمة لاحقًا.", domains: ["Documents", "OCR", "Translation", "Arabic/English"], outputs: "Document intake plan وTranslation workflow.", runtimeGate: "No OCR/STT runtime" },
  { id: "qa_security_devops", title: "وكلاء الجودة والأمن وDevOps", role: "يجهز فحصًا وتصميمًا للجودة والأمن والتشغيل دون أوامر نظام.", domains: ["QA", "Security", "DevOps", "UAT"], outputs: "Test plan وSecurity checklist وDevOps readiness.", runtimeGate: "No Shell/Docker/Git" },
];

const DOMAIN_CAPABILITY_MATRIX: DomainCapability[] = [
  { id: "flutter", title: "Flutter / Dart", currentUse: "تصميم قوالب وخطط ومهام فقط.", futureTools: "flutter_analyze, flutter_test, widget map لاحقًا.", agents: ["Frontend", "QA", "Architect"], state: "future_gate", nextGate: "FLUTTER_DART_TOOLING_READINESS_GATE" },
  { id: "react", title: "React / Next.js", currentUse: "الواجهة الحالية React/Vite ويمكن توسيعها ضمن prepare-only.", futureTools: "component generator, Playwright visual checks لاحقًا.", agents: ["Frontend", "UX", "QA"], state: "current_prepare", nextGate: "REACT_COMPONENT_TOOLING_GATE" },
  { id: "supabase", title: "Supabase / SQL / DB", currentUse: "تصميم عقود وجداول ومخططات فقط.", futureTools: "Supabase CLI, SQL migration generator, type generator لاحقًا.", agents: ["Backend", "Architect", "Security"], state: "future_gate", nextGate: "DB_PERSISTENCE_AND_SUPABASE_GATE" },
  { id: "gis", title: "GIS / Maps / Aerial", currentUse: "تحليل نطاق وتحديد أنواع ملفات وخرائط فقط.", futureTools: "GeoJSON/Shapefile/GeoTIFF readers, map renderer, coordinate converter.", agents: ["GIS", "Backend", "Frontend"], state: "future_gate", nextGate: "GIS_READONLY_PROCESSING_GATE" },
  { id: "documents", title: "Documents / OCR", currentUse: "Document Reader مؤجل/محكوم، لا OCR runtime الآن.", futureTools: "MarkItDown, Apache Tika, Tesseract OCR.", agents: ["Documents", "Knowledge", "QA"], state: "future_gate", nextGate: "DOCUMENT_READER_READONLY_GATE" },
  { id: "translation", title: "Translation", currentUse: "تصميم workflow فقط بين العربية/الإنجليزية.", futureTools: "Argos Translate, LibreTranslate, model-assisted review.", agents: ["Documents", "Arabic Governance", "Knowledge"], state: "future_gate", nextGate: "LOCAL_TRANSLATION_READINESS_GATE" },
  { id: "devops", title: "DevOps / Docker / CI", currentUse: "قوائم فحص وتصميم فقط.", futureTools: "Docker SDK, compose generator, CI templates.", agents: ["DevOps", "QA", "Security"], state: "blocked_runtime", nextGate: "SANDBOXED_DEVOPS_COMMAND_GATE" },
  { id: "execution", title: "Shell / Git / Code Execution", currentUse: "غير متاح من صفحات التشغيل.", futureTools: "قد يفتح لاحقًا فقط داخل sandbox محكوم.", agents: ["Safety", "QA", "Orchestrator"], state: "blocked_runtime", nextGate: "INDEPENDENT_EXECUTION_GOVERNANCE_GATE" },
];

function domainTone(state: DomainSupportState): "green" | "blue" | "gold" | "red" | "slate" {
  if (state === "current_prepare") return "green";
  if (state === "design_ready") return "blue";
  if (state === "future_gate") return "gold";
  return "red";
}


type EngineeringSkillPhase = "define" | "plan" | "build" | "verify" | "review" | "ship" | "meta";

type ExternalEngineeringSkill = {
  id: string;
  name: string;
  phase: EngineeringSkillPhase;
  purpose: string;
  useWhen: string;
  palwakfUse: string;
  state: "reference_only" | "mapped_prepare" | "future_gate" | "blocked_runtime";
};

const EXTERNAL_ENGINEERING_SKILLS_REFERENCE = {
  source: "addyosmani/agent-skills",
  url: "https://github.com/addyosmani/agent-skills",
  license: "MIT",
  intakeMode: "READ_ONLY_REFERENCE_SNAPSHOT",
  importedRuntime: "NO",
  installCommandAllowed: "NO",
  executionAllowed: "NO",
};

const ENGINEERING_SKILLS: ExternalEngineeringSkill[] = [
  { id: "using-agent-skills", name: "اكتشاف المهارة المناسبة", phase: "meta", purpose: "تحديد أي workflow يناسب المهمة قبل اختيار الأداة.", useWhen: "عند بداية هدف أو مهمة جديدة.", palwakfUse: "يربط Goal Planner وTask Draft بالمهارة المناسبة.", state: "mapped_prepare" },
  { id: "interview-me", name: "استجواب المتطلبات", phase: "define", purpose: "طرح أسئلة قصيرة لتوضيح الطلب غير المكتمل.", useWhen: "عندما يكون الهدف عامًا أو غامضًا.", palwakfUse: "تحسين نموذج هدف جديد قبل الخطة.", state: "reference_only" },
  { id: "idea-refine", name: "صقل الفكرة", phase: "define", purpose: "تحويل الفكرة الخام إلى اقتراح عملي.", useWhen: "قبل إنشاء خطة مشروع جديدة.", palwakfUse: "اقتراح بدائل Scope وMVP.", state: "reference_only" },
  { id: "spec-driven-development", name: "التطوير وفق المواصفة", phase: "define", purpose: "كتابة PRD وحدود ومخرجات قبل الكود.", useWhen: "مشروع أو ميزة كبيرة.", palwakfUse: "إنتاج Project Plan Draft لا تنفيذ.", state: "mapped_prepare" },
  { id: "planning-and-task-breakdown", name: "تفكيك الخطة إلى مهام", phase: "plan", purpose: "تقسيم المواصفة إلى مهام صغيرة قابلة للتحقق.", useWhen: "بعد قبول المواصفة.", palwakfUse: "توليد مسودات مهام من الهدف.", state: "mapped_prepare" },
  { id: "incremental-implementation", name: "تنفيذ شرائح صغيرة", phase: "build", purpose: "تغيير تدريجي قابل للرجوع والاختبار.", useWhen: "أي تغيير متعدد الملفات.", palwakfUse: "Future gate فقط؛ لا تنفيذ الآن.", state: "future_gate" },
  { id: "test-driven-development", name: "TDD", phase: "build", purpose: "اختبار قبل الكود، ثم Refactor.", useWhen: "منطق جديد أو إصلاح سلوك.", palwakfUse: "بوابة مستقبلية للفحص، لا تشغيل اختبارات الآن.", state: "future_gate" },
  { id: "context-engineering", name: "هندسة السياق", phase: "build", purpose: "تزويد الوكيل بالمعلومات المناسبة في الوقت المناسب.", useWhen: "تدهور جودة المخرجات أو تبديل مهمة.", palwakfUse: "يرتبط بقارئ المشروع وحالة المشروع.", state: "mapped_prepare" },
  { id: "source-driven-development", name: "التطوير الموثق بالمصدر", phase: "build", purpose: "تثبيت قرارات الأطر بمصادر رسمية.", useWhen: "Flutter/React/Supabase/GIS وأي مكتبة.", palwakfUse: "بوابة بحث/مصادر مستقبلية.", state: "future_gate" },
  { id: "frontend-ui-engineering", name: "هندسة الواجهة", phase: "build", purpose: "مكونات، تصميم، responsive، accessibility.", useWhen: "تعديل واجهة المستخدم.", palwakfUse: "يدعم صقل UX الحالي كمرجع workflow.", state: "mapped_prepare" },
  { id: "api-and-interface-design", name: "تصميم API والعقود", phase: "build", purpose: "Contract-first وحدود الأخطاء والتحقق.", useWhen: "Backend/API/module boundary.", palwakfUse: "يرتبط بعقود Backend/Frontend Alignment.", state: "mapped_prepare" },
  { id: "browser-testing-with-devtools", name: "فحص المتصفح", phase: "verify", purpose: "DOM/console/network/performance runtime data.", useWhen: "واجهة تعمل في المتصفح.", palwakfUse: "Future gate للفحص الآلي؛ الآن فحص بصري يدوي.", state: "future_gate" },
  { id: "debugging-and-error-recovery", name: "تشخيص الأخطاء والاسترداد", phase: "verify", purpose: "reproduce/localize/reduce/fix/guard.", useWhen: "فشل build أو route أو سلوك.", palwakfUse: "يدعم Stop Rules والتصحيح الضيق.", state: "mapped_prepare" },
  { id: "code-review-and-quality", name: "مراجعة الكود والجودة", phase: "review", purpose: "مراجعة بخمسة محاور قبل الدمج.", useWhen: "قبل قبول أي تغيير.", palwakfUse: "يرتبط بصفحة المراجعات، بدون Git.", state: "mapped_prepare" },
  { id: "security-and-hardening", name: "الأمن والتقوية", phase: "review", purpose: "OWASP، الأسرار، الاعتماديات، الحدود.", useWhen: "مدخلات مستخدم أو Auth أو تخزين.", palwakfUse: "Future gate عند فتح DB أو API writes.", state: "future_gate" },
  { id: "performance-optimization", name: "تحسين الأداء", phase: "review", purpose: "قياس قبل التحسين.", useWhen: "وجود مطلب أداء أو تراجع.", palwakfUse: "بوابة مستقبلية بعد تشغيل أولي.", state: "future_gate" },
  { id: "documentation-and-adrs", name: "التوثيق وADRs", phase: "ship", purpose: "توثيق لماذا لا ماذا فقط.", useWhen: "قرار معماري أو عقد API.", palwakfUse: "مرتبط بالتوريث والميثاق.", state: "mapped_prepare" },
  { id: "observability-and-instrumentation", name: "المراقبة والتتبع", phase: "ship", purpose: "Logs/metrics/tracing.", useWhen: "أي شيء سيعمل في production.", palwakfUse: "لاحقًا عند فتح runtime حقيقي.", state: "future_gate" },
  { id: "shipping-and-launch", name: "الإطلاق", phase: "ship", purpose: "Checklist، rollout، rollback.", useWhen: "قبل نشر أو تشغيل إنتاجي.", palwakfUse: "محجوب حتى توجد بوابات تنفيذ.", state: "blocked_runtime" },
];

const SKILL_PHASE_LABEL: Record<EngineeringSkillPhase, string> = {
  meta: "Meta",
  define: "Define",
  plan: "Plan",
  build: "Build",
  verify: "Verify",
  review: "Review",
  ship: "Ship",
};

function skillTone(state: ExternalEngineeringSkill["state"]): "green" | "blue" | "gold" | "red" | "slate" {
  if (state === "mapped_prepare") return "green";
  if (state === "reference_only") return "blue";
  if (state === "future_gate") return "gold";
  return "red";
}

function EngineeringSkillsRegistryPage() {
  const phaseOrder: EngineeringSkillPhase[] = ["meta", "define", "plan", "build", "verify", "review", "ship"];
  const mappedCount = ENGINEERING_SKILLS.filter((skill) => skill.state === "mapped_prepare").length;
  const futureCount = ENGINEERING_SKILLS.filter((skill) => skill.state === "future_gate").length;
  return <Layout eyebrow="مهارات هندسية" title="سجل مهارات التطوير الهندسية">
    <section className="ux-hero skills-hero">
      <div>
        <p>External Skills Reference Intake</p>
        <h2>نجلب منهجية agent-skills كمرجع عمل، لا كتثبيت أو تنفيذ</h2>
        <span>هذه الصفحة تحوّل مستودع agent-skills إلى سجل مهارات داخلي: Spec → Plan → Build → Verify → Review → Ship. كل مهارة هنا reference-only أو prepare-only حتى تفتح بوابة مستقلة.</span>
        <div className="ux-hero-actions"><a href="/agent-console/goal-planner">اربطها بهدف</a><a href="/agent-console/tasks">حوّلها لمسودات</a></div>
      </div>
      <aside>
        <strong>Intake Mode</strong>
        <small>{EXTERNAL_ENGINEERING_SKILLS_REFERENCE.intakeMode}</small>
        <b>{ENGINEERING_SKILLS.length}</b>
        <span>مهارة مرجعية مصنفة</span>
      </aside>
    </section>

    <section className="initial-readiness compact skills-intake-summary">
      <div className="initial-readiness-metrics">
        <MetricCard icon="tool" label="Mapped" value={String(mappedCount)} detail="تستخدم كـ workflow تحضيري" tone="green"/>
        <MetricCard icon="shield" label="Reference" value="3" detail="مرجع قراءة فقط" tone="blue"/>
        <MetricCard icon="lock" label="Future-gated" value={String(futureCount)} detail="تحتاج بوابة لاحقة" tone="gold"/>
      </div>
    </section>

    <section className="section-block skills-reference-card">
      <SectionHeading eyebrow="Reference Manifest" title="مصدر خارجي تحت الحجر المرجعي" detail="لا يوجد clone أو npx أو plugin install. هذا استيعاب تصميمي فقط."/>
      <div className="reader-list compact">
        <div className="reader-row"><strong>Source</strong><span>{EXTERNAL_ENGINEERING_SKILLS_REFERENCE.source}</span></div>
        <div className="reader-row"><strong>URL</strong><span>{EXTERNAL_ENGINEERING_SKILLS_REFERENCE.url}</span></div>
        <div className="reader-row"><strong>License</strong><span>{EXTERNAL_ENGINEERING_SKILLS_REFERENCE.license}</span></div>
        <div className="reader-row"><strong>Install</strong><span>Blocked: no npx / no git / no plugin</span></div>
      </div>
    </section>

    {phaseOrder.map((phase) => {
      const phaseSkills = ENGINEERING_SKILLS.filter((skill) => skill.phase === phase);
      if (phaseSkills.length === 0) return null;
      return <section className="section-block skill-phase-section" key={phase}>
        <SectionHeading eyebrow={SKILL_PHASE_LABEL[phase]} title={`مهارات مرحلة ${SKILL_PHASE_LABEL[phase]}`} detail="كل بطاقة تعرض كيف نستفيد من المهارة داخل مشروعنا دون فتح التنفيذ."/>
        <div className="skills-grid">
          {phaseSkills.map((skill) => <article className={`skill-card state-${skill.state}`} key={skill.id}>
            <div><Badge tone={skillTone(skill.state)}>{skill.state}</Badge><code>{skill.id}</code></div>
            <strong>{skill.name}</strong>
            <p>{skill.purpose}</p>
            <small>متى تستخدم: {skill.useWhen}</small>
            <span>{skill.palwakfUse}</span>
          </article>)}
        </div>
      </section>;
    })}

    <BoundaryPanel title="المهارات لا تعني تشغيلًا" detail="هذه الدفعة لا تفعّل /build auto ولا npx ولا git clone ولا أي تنفيذ. المهارات تتحول إلى عقود workflow داخلية، ثم تخضع كل قدرة لبوابة مستقلة."/>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function SpecializedAgentCatalogPage() {
  return <Layout eyebrow="مجالات التخصص" title="الوكلاء المتخصصون ومصفوفة القدرات">
    <section className="ux-hero domain-hero">
      <div>
        <p>Specialized Agent Catalog</p>
        <h2>منصة هندسية متعددة الوكلاء، لا وكيل واحد لكل شيء</h2>
        <span>هذه الصفحة تعرض المجالات التي سيدعمها المشروع تدريجيًا: Flutter/Dart، React، Supabase، GIS، قراءة المستندات، OCR، الترجمة، الجودة والأمن وDevOps. العرض تصميمي وتحضيري فقط ولا يفتح تنفيذًا.</span>
        <div className="ux-hero-actions"><a href="/agent-console/goal-planner">ابدأ هدفًا</a><a href="/agent-console/tools">اختر مساعدًا</a></div>
      </div>
      <aside>
        <strong>قدرات مستقبلية</strong>
        <small>Capability Matrix</small>
        <b>{DOMAIN_CAPABILITY_MATRIX.length}</b>
        <span>مجالات مصنفة عبر بوابات مستقلة</span>
      </aside>
    </section>

    <section className="section-block domain-agent-section">
      <SectionHeading eyebrow="Agent Roles" title="فريق وكلاء مقترح" detail="كل وكيل يمثل دورًا هندسيًا. حاليًا يخطط ويقترح ويحضّر فقط؛ لا يكتب ولا ينفذ ولا يشغل أوامر."/>
      <div className="domain-agent-grid">
        {SPECIALIZED_AGENT_ROLES.map((agent) => <article className="domain-agent-card" key={agent.id}>
          <div className="domain-card-head"><Icon name="agent" size={18}/><Badge tone="blue">design-only</Badge></div>
          <strong>{agent.title}</strong>
          <p>{agent.role}</p>
          <div className="domain-chip-row">{agent.domains.map((domain) => <span key={domain}>{domain}</span>)}</div>
          <small>{agent.outputs}</small>
          <code>{agent.runtimeGate}</code>
        </article>)}
      </div>
    </section>

    <section className="section-block domain-capability-section">
      <SectionHeading eyebrow="Domain Capability Matrix" title="ماذا ندعم الآن وماذا ينتظر بوابة لاحقة؟" detail="كل مجال يدخل عبر Tool Registry وCapability Matrix ثم Readiness Gate؛ لا يوجد فتح تلقائي للأدوات الثقيلة."/>
      <div className="domain-capability-table">
        {DOMAIN_CAPABILITY_MATRIX.map((domain) => <article className={`domain-capability-row state-${domain.state}`} key={domain.id}>
          <div><strong>{domain.title}</strong><span>{domain.currentUse}</span></div>
          <p>{domain.futureTools}</p>
          <div className="domain-agent-tags">{domain.agents.map((agent) => <small key={agent}>{agent}</small>)}</div>
          <Badge tone={domainTone(domain.state)}>{domain.state}</Badge>
          <code>{domain.nextGate}</code>
        </article>)}
      </div>
    </section>

    <BoundaryPanel title="هذه الصفحة لا تفتح التنفيذ" detail="Flutter وReact وSupabase وGIS وOCR والترجمة وDevOps تظهر هنا كقدرات تصميمية ومجالات مستقبلية. أي تشغيل فعلي يحتاج Gate مستقل وتفويض واضح." />
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalHome() {
  const drafts = useTaskDrafts();
  return <Layout eyebrow="تشغيل يومي" title="مركز العمل">
    <section className="ux-hero">
      <div>
        <p>Operational UX First</p>
        <h2>ابدأ من الهدف، لا من الحوكمة</h2>
        <span>هذه الواجهة أصبحت موجهة للمستخدم: هدف، خطة، مسودة، مراجعة. التفاصيل الحاكمة موجودة في صفحات فرعية ولا تسيطر على شاشة العمل.</span>
        <div className="ux-hero-actions"><a href="/agent-console/goal-planner">بدء هدف جديد</a><a href="/agent-console/tasks">عرض المهام</a></div>
      </div>
      <aside>
        <strong>الحالة الحالية</strong>
        <small>تشغيل آمن / Prepare-only</small>
        <b>{drafts.drafts.length}</b>
        <span>مسودات محلية ظاهرة للمراجعة</span>
      </aside>
    </section>
    <OperationalActionCards />
    <OperationalFlowPanel />
    <section className="content-grid primary-grid ux-home-secondary">
      <article className="reader-panel">
        <SectionHeading eyebrow="آخر ما يهم المستخدم" title="ما الذي أصبح جاهزًا؟" detail="ملخص عملي بعيد عن تفاصيل الأدلة."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>Goal Planner</strong><span>إدخال هدف وخطة أدوات</span></div>
          <div className="reader-row"><strong>Task Drafts</strong><span>تحضير مسودة عبر Backend prepare</span></div>
          <div className="reader-row"><strong>Review Flow</strong><span>Draft → Review → Accepted as Plan</span></div>
          <div className="reader-row"><strong>Project Reader</strong><span>قراءة بنية المشروع بدون تنفيذ</span></div>
          <div className="reader-row"><strong>Domain Matrix</strong><span>Flutter / React / Supabase / GIS / Documents / Translation كقدرات مستقبلية محكومة</span></div>
        </div>
      </article>
      <article className="reader-panel">
        <SectionHeading eyebrow="ما لا يحدث تلقائيًا" title="اطمئنان مختصر" detail="مختصر فقط؛ التفاصيل في الميثاق والتشخيص."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>التنفيذ</strong><span>محجوب</span></div>
          <div className="reader-row"><strong>النموذج المحلي</strong><span>غير مشغّل</span></div>
          <div className="reader-row"><strong>Shell / Git</strong><span>غير مستخدم</span></div>
          <div className="reader-row"><strong>Self-Apply</strong><span>مرفوض</span></div>
        </div>
      </article>
    </section>
    <OperationalGovernanceLinks />
  </Layout>;
}


type GoalTemplateId = "internal_tasks" | "admin_dashboard" | "api_service" | "knowledge_workspace" | "uat_review" | "data_workflow";

type GoalProductTemplate = {
  id: GoalTemplateId;
  title: string;
  summary: string;
  goal: string;
  projectType: string;
  deliverable: string;
  audience: string;
  constraints: string;
};

type ProductizedPlanStep = {
  id: string;
  title: string;
  assistantId: string;
  toolIds: string[];
  summary: string;
  acceptance: string;
};

const GOAL_PRODUCT_TEMPLATES: GoalProductTemplate[] = [
  { id: "internal_tasks", title: "نظام مهام داخلي", summary: "هدف Full-stack شائع: واجهة عربية، Backend API، ومراجعة قبل التنفيذ.", goal: "ابنِ نظامًا داخليًا لإدارة المهام والفرق، بواجهة عربية RTL، وBackend API، وحالات مراجعة قبل أي تنفيذ.", projectType: "Full-stack internal system", deliverable: "Plan + task drafts", audience: "فريق إداري/تشغيلي داخلي", constraints: "لا تنفيذ تلقائي، لا Git، لا Shell، خطة قابلة للمراجعة أولًا" },
  { id: "admin_dashboard", title: "لوحة تشغيل", summary: "تحويل هدف إداري إلى شاشة تشغيل ومؤشرات ومرشحات.", goal: "صمّم لوحة تشغيل للمشرف تعرض مؤشرات الحالة، المهام المفتوحة، آخر المراجعات، وروابط الإجراءات اليومية.", projectType: "Operational dashboard", deliverable: "UI plan + component tasks", audience: "مشرف تشغيل", constraints: "واجهة مستخدم بسيطة، الحوكمة في صفحات فرعية" },
  { id: "api_service", title: "خدمة Backend API", summary: "تحديد عقود API ونطاقها بدون تعديل خادمي مباشر.", goal: "حضّر خطة خدمة Backend API لإدارة عناصر مشروع جديد مع عقود endpoints، حالات الخطأ، وحدود الصلاحيات.", projectType: "Backend API service", deliverable: "API contract draft", audience: "مطور Backend", constraints: "لا تعديل Backend الآن، العقود فقط" },
  { id: "knowledge_workspace", title: "مساحة معرفة", summary: "تجهيز مسار ملفات/معرفة بدون RAG فعلي الآن.", goal: "حضّر مساحة معرفة محلية لقراءة ملفات المشروع وتصنيفها وتحويلها لاحقًا إلى معرفة قابلة للبحث.", projectType: "Knowledge workspace", deliverable: "Read model plan", audience: "محلل معرفة/مطور", constraints: "لا embeddings، لا vector DB، قراءة فقط" },
  { id: "uat_review", title: "حزمة UAT ومراجعة", summary: "تحويل طلب فحص إلى خطة تحقق قصيرة ومفهومة.", goal: "جهز خطة UAT قصيرة لفحص الصفحات الرئيسية والتأكد أن المسار التشغيلي واضح ولا توجد أزرار تنفيذ محظورة.", projectType: "UAT review flow", deliverable: "Review checklist + drafts", audience: "مختبر/مراجع", constraints: "فحص بصري ووظيفي خفيف، لا تشغيل أدوات خطرة" },
  { id: "data_workflow", title: "تدفق بيانات مساعد", summary: "تخطيط تطبيق مساعد لمعالجة بيانات بدون تشغيل تحليل فعلي.", goal: "حضّر خطة تطبيق مساعد يستقبل ملف بيانات، يعرض ملخصًا، ويقترح خطوات تنظيف وتحليل لاحقة.", projectType: "Supporting data workflow", deliverable: "Workflow plan", audience: "محلل نظم", constraints: "لا تنفيذ Python، لا قراءة ملفات خارج النطاق" },
];

function buildProductizedPlan(goal: string, template: GoalProductTemplate, priority: string): ProductizedPlanStep[] {
  const trimmed = goal.trim() || template.goal;
  const commonSuffix = `\n\nالهدف المرجعي: ${trimmed}\nنوع المشروع: ${template.projectType}\nالأولوية: ${priority}\nالحدود: ${template.constraints}`;
  return [
    { id: "scope", title: "تحليل النطاق ومعايير القبول", assistantId: "task_analyst", toolIds: ["task_planner", "tool_registry"], summary: `تحويل الهدف إلى نطاق واضح، افتراضات، مخاطر، ومعايير قبول.${commonSuffix}`, acceptance: "نطاق مفهوم، مخرجات محددة، وقيود مصرح بها." },
    { id: "architecture", title: "خطة البنية والصفحات/العقود", assistantId: template.id === "api_service" ? "backend_reader" : "coordinator", toolIds: ["project_reader", "route_api_reader"], summary: `اقتراح هيكل عالي المستوى: صفحات، عقود API، وتدفق مراجعة بدون تنفيذ.${commonSuffix}`, acceptance: "خريطة مكونات/عقود قابلة للمراجعة." },
    { id: "ux", title: "تجربة المستخدم والمخرجات اليومية", assistantId: template.id === "api_service" ? "backend_reader" : "ux_reviewer", toolIds: ["task_planner", "project_reader"], summary: `تبسيط تجربة المستخدم وربطها بمسار تشغيل يومي، مع نقل الحوكمة إلى تفاصيل فرعية.${commonSuffix}`, acceptance: "مسار مستخدم واضح، لا ازدحام حوكمي في الصفحة الرئيسية." },
    { id: "tools", title: "اختيار الأدوات والمساعدين", assistantId: "safety_governor", toolIds: ["tool_registry", "evidence_summarizer"], summary: `تحديد الأدوات المسموحة والمؤجلة والمرفوضة لهذا الهدف، وإظهار أن الاختيار ليس تشغيلًا.${commonSuffix}`, acceptance: "Tool Selection Matrix محكومة وحدود واضحة." },
    { id: "review", title: "تجهيز قرار المراجعة", assistantId: "uat_tester", toolIds: ["task_planner", "evidence_summarizer"], summary: `تحضير Checklist ومخرجات مراجعة: Accepted as Plan أو Returned، بدون Apply أو تنفيذ.${commonSuffix}`, acceptance: "قرار بشري واضح يفصل الخطة عن أي تنفيذ مستقبلي." },
  ];
}

function OperationalGoalPlanner() {
  const draftStore = useTaskDrafts();
  const [templateId, setTemplateId] = useState<GoalTemplateId>("internal_tasks");
  const selectedTemplate = GOAL_PRODUCT_TEMPLATES.find((template) => template.id === templateId) ?? GOAL_PRODUCT_TEMPLATES[0];
  const [goal, setGoal] = useState(selectedTemplate.goal);
  const [projectType, setProjectType] = useState(selectedTemplate.projectType);
  const [deliverable, setDeliverable] = useState(selectedTemplate.deliverable);
  const [audience, setAudience] = useState(selectedTemplate.audience);
  const [constraints, setConstraints] = useState(selectedTemplate.constraints);
  const [priority, setPriority] = useState("normal");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("اختر قالبًا أو اكتب هدفًا ثم حضّر مسودات الخطة للمراجعة.");
  const normalizedGoal = goal.trim() || "هدف غير محدد";
  const planSteps = useMemo(() => buildProductizedPlan(normalizedGoal, { ...selectedTemplate, projectType, deliverable, audience, constraints }, priority), [normalizedGoal, selectedTemplate, projectType, deliverable, audience, constraints, priority]);

  const applyTemplate = (template: GoalProductTemplate) => {
    setTemplateId(template.id);
    setGoal(template.goal);
    setProjectType(template.projectType);
    setDeliverable(template.deliverable);
    setAudience(template.audience);
    setConstraints(template.constraints);
    setNotice(`تم اختيار قالب: ${template.title}. الخطة المعروضة تحضيرية فقط.`);
  };

  const preparePlanDrafts = async () => {
    if (busy) return;
    setBusy(true);
    let backendPrepared = 0;
    let fallbackPrepared = 0;
    try {
      for (const step of planSteps) {
        const agent = getAgentById(step.assistantId);
        const outcome = await prepareDraftWithBackend(agent, step.title, `${step.summary}

معيار القبول: ${step.acceptance}

الناتج المطلوب: ${deliverable}
المستخدم المستهدف: ${audience}`);
        draftStore.addDraft(outcome.draft);
        if (outcome.mode === "backend_prepare") backendPrepared += 1;
        else fallbackPrepared += 1;
      }
      setNotice(`تم تحضير ${planSteps.length} مسودات من الخطة: Backend=${backendPrepared} / Browser fallback=${fallbackPrepared}. لا حفظ دائم ولا تنفيذ.`);
    } finally {
      setBusy(false);
    }
  };

  return <Layout eyebrow="هدف جديد" title="حوّل الهدف إلى خطة ومسودات عمل">
    <section className="ux-page-lead productized-goal-lead"><Icon name="task" size={26}/><div><p>Goal Planner Productization</p><h2>اكتب الهدف، اختر قالبًا، ثم حضّر مسودات مهام قابلة للمراجعة — بدون تشغيل نموذج أو بناء مشروع.</h2></div></section>

    <section className="section-block goal-template-section"><SectionHeading eyebrow="قوالب أهداف جاهزة" title="ابدأ من سيناريو عملي" detail="القوالب تختصر صياغة الهدف وتنتج خطة تحضيرية مفهومة للمستخدم."/>
      <div className="goal-template-grid">
        {GOAL_PRODUCT_TEMPLATES.map((template) => <button key={template.id} type="button" className={template.id === templateId ? "active" : ""} onClick={() => applyTemplate(template)}>
          <strong>{template.title}</strong><span>{template.summary}</span><small>{template.projectType}</small>
        </button>)}
      </div>
    </section>

    <section className="content-grid primary-grid goal-intake-grid">
      <article className="composer-card goal-intake-card ux-focus-card">
        <div className="composer-head"><div><p>الهدف</p><h2>ما المشروع أو التحسين المطلوب؟</h2><span>هذه البيانات تستخدم لتوليد خطة محلية deterministic داخل الواجهة، ولا ترسل إلى نموذج.</span></div><Badge tone="green">Prepare-only</Badge></div>
        <div className="form-grid">
          <label className="wide">الهدف<textarea value={goal} onChange={(event) => setGoal(event.target.value)} /></label>
          <label>نوع المشروع<input value={projectType} onChange={(event) => setProjectType(event.target.value)} /></label>
          <label>الناتج المطلوب<input value={deliverable} onChange={(event) => setDeliverable(event.target.value)} /></label>
          <label>المستخدم المستهدف<input value={audience} onChange={(event) => setAudience(event.target.value)} /></label>
          <label>الأولوية<select value={priority} onChange={(event) => setPriority(event.target.value)}><option value="low">منخفضة</option><option value="normal">عادية</option><option value="high">مرتفعة</option></select></label>
          <label className="wide">القيود<textarea value={constraints} onChange={(event) => setConstraints(event.target.value)} /></label>
        </div>
        <div className="composer-actions"><button className="primary-action" type="button" onClick={preparePlanDrafts} disabled={busy}><Icon name="task" size={15}/> {busy ? "جار تحضير المسودات..." : "تحضير مسودات من الخطة"}</button><DisabledButton icon="agent">تحليل بنموذج — محجوب</DisabledButton><DisabledButton icon="lock">بناء المشروع — لاحقًا</DisabledButton></div>
        <p className="goal-productization-notice">{notice}</p>
      </article>
      <article className="reader-panel goal-preview-card ux-focus-card">
        <SectionHeading eyebrow="Plan Preview" title="معاينة الخطة المنتجة" detail="الخطة تتغير حسب القالب والحقول، لكنها لا تنفذ ولا تحفظ في قاعدة بيانات."/>
        <div className="reader-list compact">
          <div className="reader-row"><strong>الهدف</strong><span>{normalizedGoal}</span></div>
          <div className="reader-row"><strong>نوع المشروع</strong><span>{projectType}</span></div>
          <div className="reader-row"><strong>الناتج</strong><span>{deliverable}</span></div>
          <div className="reader-row"><strong>عدد خطوات الخطة</strong><span>{planSteps.length}</span></div>
          <div className="reader-row"><strong>المحظورات</strong><span>Model / Shell / Git / Code execution / self-apply</span></div>
        </div>
      </article>
    </section>

    <section className="section-block productized-plan-section"><SectionHeading eyebrow="Project Plan Draft" title="الخطة الأولية القابلة للمراجعة" detail="كل بطاقة يمكن تحويلها إلى مسودة مهمة عبر Backend prepare أو Browser fallback، بدون حفظ دائم."/>
      <div className="productized-plan-grid">
        {planSteps.map((step, index) => <article key={step.id} className="productized-plan-card">
          <span>{String(index + 1).padStart(2, "0")}</span><div><strong>{step.title}</strong><p>{step.summary}</p><small>معيار القبول: {step.acceptance}</small></div>
          <div className="tool-chip-row wide">{step.toolIds.map((toolId) => <em key={toolId}>{getToolById(toolId)?.name ?? toolId}</em>)}</div>
          <Badge tone="gold">{getAgentById(step.assistantId).name}</Badge>
        </article>)}
      </div>
    </section>

    <section className="section-block"><SectionHeading eyebrow="ربط الخطة بالمهام" title="بعد التحضير" detail="المسودات الناتجة تظهر في صفحة المهام، ويمكن إرسالها للمراجعة أو قبولها كخطة فقط."/>
      <div className="goal-next-actions"><a href="/agent-console/tasks"><Icon name="task" size={15}/> عرض مسودات المهام</a><a href="/agent-console/reviews"><Icon name="review" size={15}/> فتح المراجعات</a><a href="/agent-console/state-manager"><Icon name="project" size={15}/> تفاصيل الحالة</a></div>
    </section>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalTasks() {
  const draftStore = useTaskDrafts();
  const [agentId, setAgentId] = useState(ASSISTANT_CATALOG[0].id);
  const selectedAgent = getAgentById(agentId);
  const handleBackendDraft = async (agent: CatalogAgent, title: string, description: string) => {
    const outcome = await prepareDraftWithBackend(agent, title, description);
    draftStore.addDraft(outcome.draft);
  };
  return <Layout eyebrow="المهام والخطط" title="مسودات المهام والمراجعة">
    <section className="ux-page-lead"><Icon name="task" size={26}/><div><p>Task Workspace</p><h2>كل شيء هنا يدور حول المسودة: إنشاؤها، مراجعتها، وقبولها كخطة فقط.</h2></div></section>
    <section id="local-drafts" className="section-block"><SectionHeading eyebrow="المسودات" title="المسودات الحالية" detail="تظهر هنا المسودات المحضّرة عبر Backend prepare أو fallback محلي."/><LocalDraftsPanel drafts={draftStore.drafts} onClear={draftStore.clearDrafts} onTransition={draftStore.transitionDraft}/></section>
    <section className="content-grid primary-grid">
      <TaskComposerMock agent={selectedAgent} onPrepareDraft={handleBackendDraft}/>
      <article className="selected-agent-panel ux-focus-card"><SectionHeading eyebrow="اختيار سريع" title="المساعد المناسب" detail="اختر مساعدًا ثم حضّر مسودة للمراجعة."/><div className="agent-select-list">{ASSISTANT_CATALOG.slice(0, 8).map((agent) => <button key={agent.id} type="button" className={agent.id === agentId ? "active" : ""} onClick={() => setAgentId(agent.id)}><Icon name={agent.icon} size={15}/>{agent.name}</button>)}</div></article>
    </section>
    <TaskDraftReviewFlowPanel drafts={draftStore.drafts} />
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalTools() {
  return <Layout eyebrow="المساعدون والأدوات" title="اختر المساعد المناسب">
    <section className="ux-page-lead"><Icon name="tool" size={26}/><div><p>Assistant Catalog</p><h2>الهدف هنا اختيار المساعد وبداية مسودة، وليس قراءة تفاصيل حوكمة طويلة.</h2></div></section>
    <AssistantCatalogConsole />
    <section className="section-block ux-approved-tools"><SectionHeading eyebrow="الأدوات المتاحة الآن" title="المقبول للاستخدام التحضيري" detail="عرض مختصر للأدوات المقبولة فقط؛ المؤجل والمرفوض في صفحات الحوكمة."/><div className="ux-tool-list">{LOCAL_TOOL_REGISTRY.filter((tool) => tool.status === "approved").map((tool) => <article key={tool.id}><strong>{tool.name}</strong><span>{tool.purpose}</span><Badge tone="green">prepare/read-only</Badge></article>)}</div></section>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalProjects() {
  const projectReader = useRead<UnknownRecord>(`/api/v1/project-reader/workspaces/${DEFAULT_WORKSPACE}/summary`);
  const projectReaderHealth = useRead<UnknownRecord>("/api/v1/project-reader/health");
  return <Layout eyebrow="قراءة المشروع" title="خريطة المشروع للمستخدم">
    <section className="ux-page-lead"><Icon name="project" size={26}/><div><p>Project Reader</p><h2>اعرف بنية المشروع والمسارات والملفات الرئيسية بدون الدخول في تفاصيل حوكمة كل طبقة.</h2></div></section>
    <StateGate state={projectReaderHealth} label="صحة قارئ المشروع">{(data) => <section className="health-banner ux-health-compact"><MetricCard icon="pulse" label="الخدمة" value={text(asRecord(data).service, "project-reader")} detail="GET-only" tone="blue"/><MetricCard icon="shield" label="الحالة" value={safeStatus(asRecord(data).status, "READY")} detail="أداة مقبولة" tone="gold"/><MetricCard icon="lock" label="التنفيذ" value="محجوب" detail="قراءة فقط" tone="red"/></section>}</StateGate>
    <StateGate state={projectReader} label="ملخص قراءة المشروع">{(data) => <ProjectReaderSummaryPanel data={asRecord(data)}/>}</StateGate>
    <section className="section-block"><SectionHeading eyebrow="ماذا بعد القراءة؟" title="استخدم الخريطة لتجهيز مهمة" detail="بعد قراءة المشروع، انتقل إلى الهدف أو المهام لتحضير خطة عمل."/><OperationalActionCards items={[OPERATIONAL_NEXT_ACTIONS[0], OPERATIONAL_NEXT_ACTIONS[1], OPERATIONAL_NEXT_ACTIONS[3]]}/></section>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalReviews() {
  const draftStore = useTaskDrafts();
  return <Layout eyebrow="المراجعات" title="قرار بشري على الخطط">
    <section className="ux-page-lead"><Icon name="review" size={26}/><div><p>Human Review Gate</p><h2>المراجعة تفصل بين المسودة والخطة المقبولة. لا توجد قفزة إلى التنفيذ.</h2></div></section>
    <TaskDraftReviewFlowPanel drafts={draftStore.drafts}/>
    <section className="section-block"><SectionHeading eyebrow="مسودات تحتاج قرارًا" title="المسودات المعروضة" detail="يمكن تغيير حالة المسودة من هنا كما في صفحة المهام."/><LocalDraftsPanel drafts={draftStore.drafts} onClear={draftStore.clearDrafts} onTransition={draftStore.transitionDraft}/></section>
    <BoundaryPanel title="قبول الخطة ليس Apply" detail="Accepted as Plan يعني أن الخطة مفهومة ومقبولة للمراجعة فقط؛ أي تنفيذ يحتاج تفويضًا مستقلًا لاحقًا."/>
  </Layout>;
}

function OperationalWorkspaces() {
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  return <Layout eyebrow="مساحة العمل" title="السياق الحالي">
    <section className="ux-page-lead"><Icon name="workspace" size={26}/><div><p>Workspace Context</p><h2>صفحة مختصرة لمعرفة المساحة التي ترتبط بها المهام والقراءة.</h2></div></section>
    <StateGate state={workspaces} label="سجل المساحات">{(data) => <WorkspaceCards data={data}/>}</StateGate>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

function OperationalEvidence() {
  return <Layout eyebrow="الأدلة والتوريث" title="ملخص الأدلة عند الحاجة">
    <section className="ux-page-lead"><Icon name="evidence" size={26}/><div><p>Evidence Subpage</p><h2>هذه الصفحة أصبحت فرعية: تستخدم عند إغلاق دفعة أو تجهيز توريث، وليست جزءًا من العمل اليومي.</h2></div></section>
    <section className="section-block"><SectionHeading eyebrow="استخدام عملي" title="متى أفتح هذه الصفحة؟" detail="عند قبول دفعة، تجهيز handoff، أو فحص حدود تطبيق."/><div className="ux-tool-list"><article><strong>ملخص قبول</strong><span>ما الذي تم قبوله بصريًا أو وظيفيًا.</span><Badge tone="blue">handoff</Badge></article><article><strong>حدود الدفعة</strong><span>ما الذي لم يتغير وما بقي محجوبًا.</span><Badge tone="gold">boundary</Badge></article><article><strong>نقطة الاستئناف</strong><span>من أين تبدأ الجلسة التالية.</span><Badge tone="green">resume</Badge></article></div></section>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

export function App() {
  const path = location.pathname.replace(/\/$/, "") || "/agent-console";
  if (path === "/agent-console" || path === "/agent-console/index.html") return <OperationalHome/>;
  if (path === "/agent-console/workspaces") return <OperationalWorkspaces/>;
  if (path === "/agent-console/tasks") return <OperationalTasks/>;
  if (path === "/agent-console/projects") return <OperationalProjects/>;
  if (path === "/agent-console/domain-capabilities") return <SpecializedAgentCatalogPage/>;
  if (path === "/agent-console/engineering-skills") return <EngineeringSkillsRegistryPage/>;
  if (path === "/agent-console/goal-planner") return <OperationalGoalPlanner/>;
  if (path === "/agent-console/tools") return <OperationalTools/>;
  if (path === "/agent-console/reviews") return <OperationalReviews/>;
  if (path === "/agent-console/evidence") return <OperationalEvidence/>;
  if (path === "/agent-console/initial-operation") return <InitialOperationReadinessPage/>;
  if (path === "/agent-console/charter") return <ProjectRealityCharter/>;
  if (path === "/agent-console/state-manager") return <ProjectStateManager/>;
  if (path === "/agent-console/diagnostics") return <Diagnostics/>;
  if (path === "/agent-console/pilot-control") return <PilotControl/>;
  return <Layout eyebrow="مسار غير مسجل" title="الصفحة غير موجودة"><BoundaryPanel title="لا يوجد انتقال" detail="ارجع إلى مركز العمل أو أحد المسارات المسجلة."/></Layout>;
}
