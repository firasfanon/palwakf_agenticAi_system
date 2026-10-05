import { Badge } from "../components/Badge";
import { Icon } from "../components/Icon";
import { Layout } from "../components/Layout";
import { BoundaryPanel, MetricCard, SectionHeading } from "../components/OperationalPanels";

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

export function ProjectRealityCharterPanel({ compact = false }: { compact?: boolean }) {
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

export function ProjectRealityCharter() {
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

export function ProjectStateManagerPanel({ compact = false }: { compact?: boolean }) {
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

export function ProjectStateManager() {
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

