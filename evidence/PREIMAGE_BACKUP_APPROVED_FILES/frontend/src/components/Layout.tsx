import type { ReactNode } from "react";

export interface NavigationItem {
  href: string;
  label: string;
  description: string;
}

export const navigation: NavigationItem[] = [
  { href: "/agent-console/", label: "مركز القيادة", description: "صحة وتشغيل" },
  { href: "/agent-console/workspaces", label: "مساحات العمل", description: "سياسات وسياق" },
  { href: "/agent-console/tasks", label: "المهام", description: "قراءة محكومة" },
  { href: "/agent-console/projects", label: "المشاريع", description: "عزل العميل" },
  { href: "/agent-console/evidence", label: "سجل الأدلة", description: "نزاهة ومراجع" },
  { href: "/agent-console/reviews", label: "المراجعات البشرية", description: "قرارات موثقة" },
  { href: "/agent-console/tools", label: "الأدوات", description: "Read / Prepare" },
  { href: "/agent-console/diagnostics", label: "التشخيص", description: "عقود الخدمة" },
  { href: "/agent-console/pilot-control", label: "الـPilot", description: "مقفل" },
];

export function Layout({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="التنقل الرئيسي">
        <div className="brand">
          <span className="brand-mark">LA</span>
          <div>
            <strong>المساعدون المحليون</strong>
            <small>React Foundation V1</small>
          </div>
        </div>
        <nav>
          {navigation.map((item) => (
            <a key={item.href} href={item.href} className={location.pathname === item.href || (item.href === "/agent-console/" && location.pathname === "/agent-console") ? "active" : ""}>
              <span>{item.label}</span>
              <small>{item.description}</small>
            </a>
          ))}
        </nav>
        <div className="scope-card">
          <strong>وضع الحوكمة</strong>
          <span>Default-Deny</span>
          <span>لا Token محفوظ</span>
          <span>لا تنفيذ نموذج</span>
        </div>
      </aside>
      <main className="content">
        <header className="topbar">
          <div>
            <p>{eyebrow}</p>
            <h1>{title}</h1>
          </div>
          <div className="runtime-badges">
            <span>React + TypeScript</span>
            <span>Read-first</span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
