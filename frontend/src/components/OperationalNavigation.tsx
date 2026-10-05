import { Icon, type IconName } from "./Icon";
import { SectionHeading } from "./OperationalPanels";

export type OperationalCard = {
  id: string;
  title: string;
  detail: string;
  href: string;
  icon: IconName;
  tone: "green" | "blue" | "gold" | "red" | "slate";
};

export const OPERATIONAL_NEXT_ACTIONS: OperationalCard[] = [
  { id: "goal", title: "ابدأ بهدف جديد", detail: "اكتب هدفًا كبيرًا ليظهر كنطاق وخطة وأدوات مقترحة، دون تنفيذ.", href: "/agent-console/goal-planner", icon: "task", tone: "green" },
  { id: "initial", title: "جاهزية التشغيل الأولي", detail: "افحص ما أصبح جاهزًا وما يبقى محجوبًا قبل أول تشغيل.", href: "/agent-console/initial-operation", icon: "pulse", tone: "gold" },
  { id: "draft", title: "حضّر مسودة مهمة", detail: "اختر مساعدًا وأنشئ Draft عبر Backend prepare مع بقاء persistence=none.", href: "/agent-console/tasks", icon: "agent", tone: "blue" },
  { id: "project", title: "اقرأ بنية المشروع", detail: "افتح خريطة المشروع والمسارات والملفات الرئيسية بصيغة قراءة آمنة.", href: "/agent-console/projects", icon: "project", tone: "gold" },
  { id: "domains", title: "مجالات التخصص", detail: "اعرف الوكلاء والمجالات التي سيدعمها المشروع تدريجيًا.", href: "/agent-console/domain-capabilities", icon: "agent", tone: "blue" },
  { id: "tools", title: "اختر المساعد المناسب", detail: "استعرض المساعدين والأدوات المقبولة دون إغراق حوكمي.", href: "/agent-console/tools", icon: "tool", tone: "slate" },
];

const OPERATIONAL_FLOW_STEPS = [
  { id: "01", title: "هدف", detail: "ماذا تريد بناءه أو فهمه؟" },
  { id: "02", title: "خطة", detail: "نطاق وخطوات وأدوات مقترحة." },
  { id: "03", title: "مسودة", detail: "Task Draft قابل للمراجعة." },
  { id: "04", title: "مراجعة", detail: "Accepted as Plan فقط، لا تنفيذ." },
];

export function OperationalGovernanceLinks({ compact = false }: { compact?: boolean }) {
  const links: OperationalCard[] = [
    { id: "charter", title: "الميثاق", detail: "الحقيقة الرسمية والحدود السيادية.", href: "/agent-console/charter", icon: "shield", tone: "gold" },
    { id: "state", title: "حالة المشروع", detail: "Goal/Plan/Review/Boundary كنموذج حالة.", href: "/agent-console/state-manager", icon: "project", tone: "blue" },
    { id: "diagnostics", title: "التشخيص", detail: "حالة الخدمات والعقود الصحية.", href: "/agent-console/diagnostics", icon: "pulse", tone: "slate" },
    { id: "pilot", title: "Pilot Control", detail: "التشغيل الحساس يبقى خلف بوابات مستقلة.", href: "/agent-console/pilot-control", icon: "lock", tone: "red" },
  ];
  const cards = <div className="ux-subpage-grid">
    {links.map((link) => <a className={`ux-subpage-card ux-tone-${link.tone}`} href={link.href} key={link.id}>
      <Icon name={link.icon} size={18}/><strong>{link.title}</strong><span>{link.detail}</span>
    </a>)}
  </div>;

  if (compact) {
    return <details className="p4-disclosure governance-disclosure">
      <summary><span><strong>الحدود والتشخيص</strong><small>افتح تفاصيل الحوكمة فقط عندما تحتاجها</small></span><b aria-hidden="true">+</b></summary>
      <div className="p4-disclosure-body">{cards}</div>
    </details>;
  }

  return <section className="section-block ux-subpages">
    <SectionHeading eyebrow="تفاصيل عند الحاجة" title="صفحات الحوكمة والتشخيص" detail="تبقى التفاصيل الحاكمة متاحة من دون أن تهيمن على رحلة العمل اليومية."/>
    {cards}
  </section>;
}

export function OperationalActionCards({ items = OPERATIONAL_NEXT_ACTIONS }: { items?: OperationalCard[] }) {
  return <section className="ux-action-grid" aria-label="إجراءات تشغيلية سريعة">
    {items.map((item) => <a className={`ux-action-card ux-tone-${item.tone}`} href={item.href} key={item.id}>
      <span><Icon name={item.icon} size={22}/></span>
      <div><strong>{item.title}</strong><p>{item.detail}</p></div>
      <i aria-hidden="true">فتح</i>
    </a>)}
  </section>;
}

export function OperationalFlowPanel() {
  return <section className="section-block ux-flow-panel">
    <SectionHeading eyebrow="Workflow" title="مسار العمل البسيط" detail="ابدأ بالقرار المطلوب، ثم اكشف التفاصيل الحاكمة عند الحاجة."/>
    <div className="ux-flow-steps">
      {OPERATIONAL_FLOW_STEPS.map((step) => <article key={step.id}><span>{step.id}</span><strong>{step.title}</strong><p>{step.detail}</p></article>)}
    </div>
  </section>;
}
