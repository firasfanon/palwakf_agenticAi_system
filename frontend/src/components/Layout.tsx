import { useState, type ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export interface NavigationItem {
  href: string;
  label: string;
  description: string;
  icon: IconName;
  section: "operational" | "governance";
}

export const navigation: NavigationItem[] = [
  { href: "/agent-console/", label: "مركز العمل", description: "ابدأ من هنا", icon: "home", section: "operational" },
  { href: "/agent-console/goal-planner", label: "هدف جديد", description: "حوّل الهدف إلى خطة", icon: "task", section: "operational" },
  { href: "/agent-console/tasks", label: "المهام والخطط", description: "مسودات ومراجعة", icon: "task", section: "operational" },
  { href: "/agent-console/tools", label: "المساعدون والأدوات", description: "اختر المساعد", icon: "tool", section: "operational" },
  { href: "/agent-console/projects", label: "قراءة المشروع", description: "خريطة وفهم", icon: "project", section: "operational" },
  { href: "/agent-console/domain-capabilities", label: "مجالات التخصص", description: "وكلاء وتقنيات", icon: "agent", section: "operational" },
  { href: "/agent-console/engineering-skills", label: "المهارات الهندسية", description: "Skills workflows", icon: "tool", section: "operational" },
  { href: "/agent-console/reviews", label: "المراجعات", description: "قرارات بشرية", icon: "review", section: "operational" },
  { href: "/agent-console/workspaces", label: "مساحة العمل", description: "السياق الحالي", icon: "workspace", section: "operational" },
  { href: "/agent-console/charter", label: "الميثاق", description: "الحقيقة والحدود", icon: "shield", section: "governance" },
  { href: "/agent-console/state-manager", label: "حالة المشروع", description: "State Model", icon: "project", section: "governance" },
  { href: "/agent-console/diagnostics", label: "التشخيص", description: "Health checks", icon: "pulse", section: "governance" },
  { href: "/agent-console/pilot-control", label: "Pilot Control", description: "مقفل الآن", icon: "lock", section: "governance" },
  { href: "/agent-console/evidence", label: "الأدلة", description: "سجلات وتوريث", icon: "evidence", section: "governance" },
];

function isActive(href: string): boolean {
  const current = location.pathname.replace(/\/$/, "") || "/agent-console";
  const target = href.replace(/\/$/, "") || "/agent-console";
  return current === target;
}

function NavigationSection({ title, items, onNavigate }: { title: string; items: NavigationItem[]; onNavigate?: () => void }) {
  return <div className="nav-section">
    <div className="sidebar-label">{title}</div>
    <nav className="primary-nav" aria-label={title}>
      {items.map((item) => <a key={item.href} href={item.href} onClick={onNavigate} className={isActive(item.href) ? "active" : ""}>
        <span className="nav-icon"><Icon name={item.icon} size={18}/></span>
        <span className="nav-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
      </a>)}
    </nav>
  </div>;
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const operational = navigation.filter((item) => item.section === "operational");
  const governance = navigation.filter((item) => item.section === "governance");
  return <>
    <NavigationSection title="التشغيل اليومي" items={operational} onNavigate={onNavigate}/>
    <NavigationSection title="تفاصيل الحوكمة والتشخيص" items={governance} onNavigate={onNavigate}/>
  </>;
}

export function Layout({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return <div className="app-shell">
    <aside className={mobileOpen ? "sidebar sidebar-open" : "sidebar"} aria-label="لوحة التنقل">
      <div className="brand-row">
        <a className="brand" href="/agent-console/" aria-label="مركز عمل المساعدين المحليين">
          <span className="brand-mark"><span>PW</span><i>AI</i></span>
          <span><strong>المساعدون المحليون</strong><small>منصة تشغيل هندسية محلية</small></span>
        </a>
        <button className="mobile-close" type="button" onClick={() => setMobileOpen(false)} aria-label="إغلاق التنقل"><Icon name="close"/></button>
      </div>
      <Navigation onNavigate={() => setMobileOpen(false)} />
      <section className="governance-card ux-help-card" aria-label="مبدأ التشغيل الحالي">
        <div className="governance-title"><Icon name="task" size={18}/><strong>طريقة العمل</strong></div>
        <p>ابدأ بهدف واضح، حوّله إلى خطة، اختر مساعدًا، ثم راجع المسودة. التفاصيل الحاكمة موجودة في الصفحات الفرعية عند الحاجة.</p>
        <ul><li>تشغيل يومي مبسط</li><li>مراجعة بشرية قبل أي انتقال</li><li>التنفيذ مؤجل ومحكوم</li></ul>
      </section>
      <p className="sidebar-footnote">Operational UX Polish R2 + Domain Matrix + Skills Intake V1</p>
    </aside>
    {mobileOpen && <button className="drawer-backdrop" type="button" aria-label="إغلاق التنقل" onClick={() => setMobileOpen(false)} />}
    <main className="content">
      <header className="topbar">
        <button className="menu-button" type="button" onClick={() => setMobileOpen(true)} aria-label="فتح التنقل"><Icon name="menu"/></button>
        <div className="page-heading"><p>{eyebrow}</p><h1>{title}</h1></div>
        <div className="read-only-badge operational-badge"><Icon name="shield" size={16}/><span>تشغيل آمن</span></div>
      </header>
      {children}
    </main>
  </div>;
}
