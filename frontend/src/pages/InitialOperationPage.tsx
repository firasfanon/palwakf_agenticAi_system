import { Badge } from "../components/Badge";
import { Icon } from "../components/Icon";
import { Layout } from "../components/Layout";
import { OperationalGovernanceLinks } from "../components/OperationalNavigation";
import { BoundaryPanel, MetricCard, SectionHeading } from "../components/OperationalPanels";
import { ProgressiveDisclosure } from "../components/ProductUI";

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

export function InitialOperationReadinessPanel({ compact = true }: { compact?: boolean }) {
  const readyCount = INITIAL_OPERATION_READINESS_ITEMS.filter((item) => item.status === "ready").length;
  const futureCount = BLOCKED_CAPABILITY_REASSESSMENT.filter((item) => item.allowedMode === "future_gate").length;
  const blockedCount = BLOCKED_CAPABILITY_REASSESSMENT.filter((item) => item.allowedMode === "blocked").length;
  return <section className={compact ? "initial-readiness compact" : "section-block initial-readiness"}>
    <div className="initial-readiness-metrics">
      <MetricCard icon="review" label="جاهز الآن" value={String(readyCount)} detail="عناصر تشغيل مقبولة" tone="gold"/>
      <MetricCard icon="shield" label="بوابات لاحقة" value={String(futureCount)} detail="تحتاج تفويضًا مستقلًا" tone="gold"/>
      <MetricCard icon="lock" label="يبقى محجوبًا" value={String(blockedCount)} detail="غير لازم للتشغيل الأولي" tone="red"/>
    </div>
  </section>;
}

export function InitialOperationReadinessPage() {
  return <Layout eyebrow="تشغيل أولي" title="جاهزية التشغيل الأولي">
    <section className="ux-hero readiness-hero">
      <div>
        <p>Initial Operation Readiness</p>
        <h2>قرار الجاهزية أولًا، والتفاصيل عند الحاجة</h2>
        <span>اعرف ما يمكن استخدامه الآن، وما ينتظر بوابة لاحقة، من دون فتح Model أو Pilot أو Shell أو Git أو Code execution.</span>
        <div className="ux-hero-actions"><a href="/agent-console/goal-planner">ابدأ سيناريو فحص</a><a href="/agent-console/tasks">عرض المسودات</a></div>
      </div>
      <aside>
        <strong>نمط المرحلة</strong>
        <small>Governed readiness</small>
        <b>0</b>
        <span>تنفيذ حساس مفتوح تلقائيًا</span>
      </aside>
    </section>
    <InitialOperationReadinessPanel />
    <section className="section-block readiness-checklist">
      <SectionHeading eyebrow="Readiness Plan" title="ما الجاهز للتشغيل الأولي؟" detail="ابدأ بهذه الخلاصة؛ افتح التفاصيل الحاكمة فقط عندما تحتاجها."/>
      <div className="readiness-card-grid">
        {INITIAL_OPERATION_READINESS_ITEMS.map((item) => <article key={item.id} className={`readiness-card status-${item.status}`}>
          <div><Icon name={item.status === "blocked" ? "lock" : item.status === "ready" ? "review" : "pulse"} size={20}/><Badge tone={readinessTone(item.status)}>{item.status}</Badge></div>
          <strong>{item.title}</strong><p>{item.evidence}</p><small>Owner: {item.owner}</small><span>{item.next}</span>
        </article>)}
      </div>
    </section>
    <ProgressiveDisclosure title="مصفوفة القدرات المحجوبة" summary="تفاصيل سبب الحجب والبوابة التالية لكل قدرة">
      <div className="capability-table">
        {BLOCKED_CAPABILITY_REASSESSMENT.map((item) => <article key={item.id} className={`capability-row mode-${item.allowedMode}`}>
          <div><strong>{item.capability}</strong><span>الحالة السابقة: {item.priorState}</span></div>
          <p>{item.reason}</p>
          <Badge tone={capabilityTone(item.allowedMode)}>{item.allowedMode}</Badge>
          <small>{item.decision}</small><code>{item.nextGate}</code>
        </article>)}
      </div>
    </ProgressiveDisclosure>
    <section className="content-grid primary-grid">
      <ProgressiveDisclosure title="خطة الفحص الأولي" summary="سبع خطوات قصيرة تغطي رحلة التشغيل المسموحة" defaultOpen>
        <div className="reader-list compact">{FIRST_RUN_TEST_PLAN.map((item, index) => <div className="reader-row" key={item}><strong>{String(index + 1).padStart(2, "0")}</strong><span>{item}</span></div>)}</div>
      </ProgressiveDisclosure>
      <ProgressiveDisclosure title="قواعد الإيقاف" summary="متى يجب أن يتوقف الفحص ويعود إلى إصلاح محكوم">
        <div className="reader-list compact">{INITIAL_OPERATION_STOP_RULES.map((item, index) => <div className="reader-row" key={item}><strong>STOP {index + 1}</strong><span>{item}</span></div>)}</div>
      </ProgressiveDisclosure>
    </section>
    <BoundaryPanel title="الجاهزية ليست تفويض تنفيذ" detail="كل قدرة حساسة تحتاج تفويضًا وبوابة مستقلة؛ الصفحة تعرض الحالة ولا تتجاوزها."/>
    <OperationalGovernanceLinks compact />
  </Layout>;
}
