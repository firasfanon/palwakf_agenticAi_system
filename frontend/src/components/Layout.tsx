import { useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { Icon } from "./Icon";
import {
  NAVIGATION_ROUTES,
  normalizeAgentPath,
  resolveAgentRoute,
  type AgentRouteDefinition,
} from "../routes";

function isActive(route: AgentRouteDefinition): boolean {
  const current = resolveAgentRoute(location.pathname);
  return current?.id === route.id;
}

function NavigationSection({ title, items, onNavigate }: {
  title: string;
  items: readonly AgentRouteDefinition[];
  onNavigate?: () => void;
}) {
  if (items.length === 0) return null;
  return <div className="nav-section">
    <div className="sidebar-label">{title}</div>
    <nav className="primary-nav" aria-label={title}>
      {items.map((item) => <a
        key={item.id}
        href={item.path === "/agent-console" ? "/agent-console/" : item.path}
        onClick={onNavigate}
        className={isActive(item) ? "active" : ""}
        aria-current={isActive(item) ? "page" : undefined}
      >
        <span className="nav-icon"><Icon name={item.icon} size={18}/></span>
        <span className="nav-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
      </a>)}
    </nav>
  </div>;
}

function Navigation({ onNavigate, searchInputRef }: { onNavigate?: () => void; searchInputRef?: RefObject<HTMLInputElement> }) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLocaleLowerCase("ar");
  const filtered = useMemo(() => NAVIGATION_ROUTES.filter((item) => {
    if (!normalizedQuery) return true;
    return [item.label, item.description, item.eyebrow, item.id]
      .join(" ")
      .toLocaleLowerCase("ar")
      .includes(normalizedQuery);
  }), [normalizedQuery]);
  const operational = filtered.filter((item) => item.section === "operational");
  const governance = filtered.filter((item) => item.section === "governance");

  return <>
    <div className="nav-search">
      <label htmlFor="agent-route-search">انتقل بسرعة</label>
      <input
        id="agent-route-search"
        ref={searchInputRef}
        type="search"
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
        placeholder="ابحث عن صفحة…"
        autoComplete="off"
      />
    </div>
    <NavigationSection title="التشغيل اليومي" items={operational} onNavigate={onNavigate}/>
    <NavigationSection title="تفاصيل الحوكمة والتشخيص" items={governance} onNavigate={onNavigate}/>
    {filtered.length === 0 && <p className="nav-empty" role="status">لا توجد صفحة مطابقة.</p>}
  </>;
}

export function Layout({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const route = resolveAgentRoute(location.pathname);

  useEffect(() => {
    if (!mobileOpen) return;
    const frame = requestAnimationFrame(() => searchInputRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [mobileOpen]);

  useEffect(() => {
    document.title = `${title} · PalWakf Agentic`;
  }, [title]);

  const closeMobileNav = () => {
    setMobileOpen(false);
    requestAnimationFrame(() => menuButtonRef.current?.focus());
  };

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">تجاوز التنقل إلى المحتوى</a>
    <aside
      id="primary-sidebar"
      className={mobileOpen ? "sidebar sidebar-open" : "sidebar"}
      aria-label="لوحة التنقل"
      onKeyDown={(event) => {
        if (mobileOpen && event.key === "Escape") {
          event.preventDefault();
          closeMobileNav();
        }
      }}
    >
      <div className="brand-row">
        <a className="brand" href="/agent-console/" aria-label="مركز عمل المساعدين المحليين">
          <span className="brand-mark"><span>PW</span><i>AI</i></span>
          <span><strong>المساعدون المحليون</strong><small>منصة تشغيل هندسية محلية</small></span>
        </a>
        <button className="mobile-close" type="button" onClick={closeMobileNav} aria-label="إغلاق التنقل"><Icon name="close"/></button>
      </div>
      <Navigation onNavigate={() => setMobileOpen(false)} searchInputRef={searchInputRef} />
      <section className="governance-card ux-help-card" aria-label="مبدأ التشغيل الحالي">
        <div className="governance-title"><Icon name="task" size={18}/><strong>طريقة العمل</strong></div>
        <p>ابدأ بالقرار الذي تريد الوصول إليه، ثم اكشف التفاصيل الحاكمة عند الحاجة. كل انتقال حساس يبقى خلف بوابته.</p>
        <ul><li>تشغيل يومي مبسط</li><li>مراجعة بشرية قبل الانتقال</li><li>تنفيذ محكوم وقابل للتدقيق</li></ul>
      </section>
      <p className="sidebar-footnote">P4 UI/UX Designer V4 · semantic design system</p>
    </aside>
    {mobileOpen && <button className="drawer-backdrop" type="button" aria-label="إغلاق التنقل" onClick={closeMobileNav} />}
    <main id="main-content" className="content" tabIndex={-1}>
      <header className="topbar">
        <button
          ref={menuButtonRef}
          className="menu-button"
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="فتح التنقل"
          aria-expanded={mobileOpen}
          aria-controls="primary-sidebar"
        ><Icon name="menu"/></button>
        <div className="page-heading">
          <p>{eyebrow}</p>
          <h1>{title}</h1>
          <div className="route-context" aria-label="مسار الصفحة">
            <a href="/agent-console/">مركز العمل</a>
            <span aria-hidden="true">/</span>
            <b>{route?.label ?? "مسار غير مسجل"}</b>
            {route && <span>{route.section === "operational" ? "تشغيل" : "حوكمة"}</span>}
          </div>
        </div>
        <div className="read-only-badge operational-badge"><Icon name="shield" size={16}/><span>تشغيل آمن</span></div>
      </header>
      {children}
    </main>
  </div>;
}
