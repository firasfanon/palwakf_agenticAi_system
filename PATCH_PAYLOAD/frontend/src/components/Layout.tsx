import { useState, type ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export interface NavigationItem {
  href: string;
  label: string;
  description: string;
  icon: IconName;
}

export const navigation: NavigationItem[] = [
  { href: "/agent-console/", label: "لوحة البداية", description: "نظرة تشغيلية", icon: "home" },
  { href: "/agent-console/workspaces", label: "مساحات العمل", description: "السياق والسياسات", icon: "workspace" },
  { href: "/agent-console/tasks", label: "المهام", description: "عرض محكوم", icon: "task" },
  { href: "/agent-console/projects", label: "المشاريع", description: "حدود العميل", icon: "project" },
  { href: "/agent-console/evidence", label: "الأدلة", description: "السجل والمراجع", icon: "evidence" },
  { href: "/agent-console/reviews", label: "المراجعات", description: "قرار بشري", icon: "review" },
  { href: "/agent-console/tools", label: "الأدوات", description: "قراءة وتحضير", icon: "tool" },
  { href: "/agent-console/diagnostics", label: "سلامة النظام", description: "عقود الخدمة", icon: "pulse" },
  { href: "/agent-console/pilot-control", label: "الـPilot", description: "مقفل حاليًا", icon: "lock" },
];

function isActive(href: string): boolean {
  const current = location.pathname.replace(/\/$/, "") || "/agent-console";
  const target = href.replace(/\/$/, "") || "/agent-console";
  return current === target;
}

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  return <nav className="primary-nav" aria-label="التنقل الرئيسي">
    {navigation.map((item) => <a key={item.href} href={item.href} onClick={onNavigate} className={isActive(item.href) ? "active" : ""}>
      <span className="nav-icon"><Icon name={item.icon} size={18}/></span>
      <span className="nav-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
    </a>)}
  </nav>;
}

export function Layout({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return <div className="app-shell">
    <aside className={mobileOpen ? "sidebar sidebar-open" : "sidebar"} aria-label="لوحة التنقل">
      <div className="brand-row">
        <a className="brand" href="/agent-console/" aria-label="لوحة بداية المساعدين المحليين">
          <span className="brand-mark"><span>PW</span><i>AI</i></span>
          <span><strong>المساعدون المحليون</strong><small>منصة PalWakf السيادية</small></span>
        </a>
        <button className="mobile-close" type="button" onClick={() => setMobileOpen(false)} aria-label="إغلاق التنقل"><Icon name="close"/></button>
      </div>
      <div className="sidebar-label">مساحات القراءة المحكومة</div>
      <Navigation onNavigate={() => setMobileOpen(false)} />
      <section className="governance-card" aria-label="حدود الحوكمة الحالية">
        <div className="governance-title"><Icon name="shield" size={18}/><strong>حدود الحوكمة</strong></div>
        <p>الواجهة تعرض فقط ما يسمح به عقد القراءة الحالي.</p>
        <ul><li>لا Token داخل المتصفح</li><li>لا تنفيذ نموذج أو Pilot</li><li>لا كتابة أو إرسال أو اعتماد</li></ul>
      </section>
      <p className="sidebar-footnote">Read-only Product Candidate V1</p>
    </aside>
    {mobileOpen && <button className="drawer-backdrop" type="button" aria-label="إغلاق التنقل" onClick={() => setMobileOpen(false)} />}
    <main className="content">
      <header className="topbar">
        <button className="menu-button" type="button" onClick={() => setMobileOpen(true)} aria-label="فتح التنقل"><Icon name="menu"/></button>
        <div className="page-heading"><p>{eyebrow}</p><h1>{title}</h1></div>
        <div className="read-only-badge"><Icon name="lock" size={16}/><span>عرض محكوم فقط</span></div>
      </header>
      {children}
    </main>
  </div>;
}
