import { Badge } from "../components/Badge";
import { Icon } from "../components/Icon";
import { Layout } from "../components/Layout";
import { OperationalGovernanceLinks } from "../components/OperationalNavigation";
import { BoundaryPanel, MetricCard, SectionHeading } from "../components/OperationalPanels";
import { ProgressiveDisclosure } from "../components/ProductUI";

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

const LOCAL_UI_UX_DESIGN_INTELLIGENCE = {
  id: "PALWAKF_UI_UX_DESIGN_INTELLIGENCE_V1",
  provider: "nextlevelbuilder/ui-ux-pro-max-skill",
  pinnedHead: "477bcb28c9812b385cb51a4605ddf30d7b2266e2",
  pinnedTree: "0041561a8accf20fcd186de04689c74377db8c16",
  mode: "LOCAL_PINNED_READ_ONLY",
  vendoredFiles: 44,
  authority: "ADVISORY_ONLY",
  executionAuthority: "NONE",
  persistenceAuthority: "NONE",
  networkAuthority: "NONE",
  identityPolicy: "PalWakf RTL + institutional operational identity remains authoritative",
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
  { id: "browser-testing-with-devtools", name: "فحص المتصفح", phase: "verify", purpose: "DOM/console/network/performance runtime data.", useWhen: "واجهة تعمل في المتصفح.", palwakfUse: "P4 يستخدمه كفحص آلي محكوم للـ1440/390 دون صلاحية كتابة.", state: "mapped_prepare" },
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

export function EngineeringSkillsRegistryPage() {
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
        <MetricCard icon="tool" label="Mapped" value={String(mappedCount)} detail="تستخدم كـ workflow تحضيري" tone="blue"/>
        <MetricCard icon="shield" label="Reference" value="3" detail="مرجع قراءة فقط" tone="blue"/>
        <MetricCard icon="lock" label="Future-gated" value={String(futureCount)} detail="تحتاج بوابة لاحقة" tone="gold"/>
      </div>
    </section>


    <section className="section-block p4-design-intelligence">
      <SectionHeading
        eyebrow="Local Design Intelligence"
        title="ذكاء تصميم محلي مثبت الإصدار"
        detail="يستخدم Agentic قاعدة UI/UX Pro Max المحلية كمرجع بحث وتصميم، بينما تبقى هوية PalWakf وسلطة القبول أعلى من أي اقتراح خارجي."
      />
      <div className="p4-provider-grid">
        <article>
          <div><Icon name="agent" size={20}/><Badge tone="green">LOCAL</Badge></div>
          <strong>{LOCAL_UI_UX_DESIGN_INTELLIGENCE.id}</strong>
          <span>{LOCAL_UI_UX_DESIGN_INTELLIGENCE.mode}</span>
          <small>{LOCAL_UI_UX_DESIGN_INTELLIGENCE.vendoredFiles} ملفًا مضمّنًا داخل حزمة Agentic</small>
        </article>
        <article>
          <div><Icon name="shield" size={20}/><Badge tone="blue">PINNED</Badge></div>
          <strong>UI/UX Pro Max</strong>
          <code>{LOCAL_UI_UX_DESIGN_INTELLIGENCE.pinnedHead.slice(0, 12)}</code>
          <small>Hash verified · لا global install · لا auto-update</small>
        </article>
        <article>
          <div><Icon name="lock" size={20}/><Badge tone="gold">ADVISORY</Badge></div>
          <strong>حدود السلطة</strong>
          <span>{LOCAL_UI_UX_DESIGN_INTELLIGENCE.authority}</span>
          <small>لا execution ولا persistence ولا network authority</small>
        </article>
      </div>
      <p className="p4-provider-policy">{LOCAL_UI_UX_DESIGN_INTELLIGENCE.identityPolicy}</p>
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

    <section className="p4-skill-phases" aria-label="مراحل المهارات الهندسية">
      {phaseOrder.map((phase) => {
        const phaseSkills = ENGINEERING_SKILLS.filter((skill) => skill.phase === phase);
        if (phaseSkills.length === 0) return null;
        const mapped = phaseSkills.filter((skill) => skill.state === "mapped_prepare").length;
        const gated = phaseSkills.filter((skill) => skill.state === "future_gate" || skill.state === "blocked_runtime").length;
        return <ProgressiveDisclosure
          key={phase}
          title={`مرحلة ${SKILL_PHASE_LABEL[phase]} · ${phaseSkills.length} مهارات`}
          summary={`${mapped} قابلة للاستخدام التحضيري · ${gated} خلف بوابات لاحقة`}
          defaultOpen={phase === "meta"}
        >
          <div className="skills-grid">
            {phaseSkills.map((skill) => <article className={`skill-card state-${skill.state}`} key={skill.id}>
              <div><Badge tone={skillTone(skill.state)}>{skill.state}</Badge><code>{skill.id}</code></div>
              <strong>{skill.name}</strong>
              <p>{skill.purpose}</p>
              <small>متى تستخدم: {skill.useWhen}</small>
              <span>{skill.palwakfUse}</span>
            </article>)}
          </div>
        </ProgressiveDisclosure>;
      })}
    </section>

    <BoundaryPanel title="المهارات لا تعني تشغيلًا" detail="هذه الدفعة لا تفعّل /build auto ولا npx ولا git clone ولا أي تنفيذ. المهارات تتحول إلى عقود workflow داخلية، ثم تخضع كل قدرة لبوابة مستقلة."/>
    <OperationalGovernanceLinks compact />
  </Layout>;
}

export function SpecializedAgentCatalogPage() {
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

    <ProgressiveDisclosure
      title={`مصفوفة مجالات التخصص · ${DOMAIN_CAPABILITY_MATRIX.length} مجالات`}
      summary="افتح التفاصيل لمعرفة الأدوات المستقبلية والوكلاء والبوابة المطلوبة لكل مجال."
    >
      <div className="domain-capability-table">
        {DOMAIN_CAPABILITY_MATRIX.map((domain) => <article className={`domain-capability-row state-${domain.state}`} key={domain.id}>
          <div><strong>{domain.title}</strong><span>{domain.currentUse}</span></div>
          <p>{domain.futureTools}</p>
          <div className="domain-agent-tags">{domain.agents.map((agent) => <small key={agent}>{agent}</small>)}</div>
          <Badge tone={domainTone(domain.state)}>{domain.state}</Badge>
          <code>{domain.nextGate}</code>
        </article>)}
      </div>
    </ProgressiveDisclosure>

    <BoundaryPanel title="هذه الصفحة لا تفتح التنفيذ" detail="Flutter وReact وSupabase وGIS وOCR والترجمة وDevOps تظهر هنا كقدرات تصميمية ومجالات مستقبلية. أي تشغيل فعلي يحتاج Gate مستقل وتفويض واضح." />
    <OperationalGovernanceLinks compact />
  </Layout>;
}

