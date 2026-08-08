import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import type { ReadState } from "../api/types";

export function StateGate<T>({ state, children, label = "بيانات تشغيلية" }: { state: ReadState<T>; children: (data: T) => ReactNode; label?: string }) {
  if (state.kind === "loading") return <section className="inline-state loading"><span className="pulse-dot"/> جارٍ قراءة {label} ضمن العقد المسموح…</section>;
  if (state.kind === "denied") return <section className="inline-state denied"><Icon name="lock"/><div><strong>البيانات غير معروضة</strong><span>الوصول مرفوض ({state.status})؛ لا تتجاوز الواجهة هذا الحد.</span></div></section>;
  if (state.kind === "error") return <section className="inline-state error"><Icon name="pulse"/><div><strong>تعذر جلب {label}</strong><span>{state.detail}</span></div></section>;
  return <>{children(state.data)}</>;
}

export function MetricCard({ icon, label, value, detail, tone = "blue" }: { icon: IconName; label: string; value: string | number; detail: string; tone?: "blue" | "gold" | "red" | "slate" }) {
  return <article className={`metric-card metric-${tone}`}>
    <span className="metric-icon"><Icon name={icon} size={21}/></span>
    <div><p>{label}</p><strong>{value}</strong><small>{detail}</small></div>
  </article>;
}

export function SectionHeading({ eyebrow, title, detail, link }: { eyebrow: string; title: string; detail?: string; link?: { href: string; label: string } }) {
  return <div className="section-heading"><div><p>{eyebrow}</p><h2>{title}</h2>{detail && <span>{detail}</span>}</div>{link && <a href={link.href} className="text-link">{link.label}<Icon name="arrow" size={16}/></a>}</div>;
}

export function BoundaryPanel({ title = "حدود هذه المرحلة", detail }: { title?: string; detail?: string }) {
  return <article className="boundary-panel">
    <div className="boundary-icon"><Icon name="shield" size={23}/></div>
    <div><p>حوكمة ثابتة</p><h2>{title}</h2><span>{detail ?? "لا توجد عناصر تحكم للكتابة أو الاعتماد أو تشغيل النموذج. تظهر الحالات والحدود كما يسمح عقد القراءة فقط."}</span></div>
  </article>;
}

export function BlockedAction({ icon, title, detail }: { icon: IconName; title: string; detail: string }) {
  return <article className="blocked-action"><span><Icon name={icon} size={20}/></span><div><strong>{title}</strong><p>{detail}</p></div><b>مقفل</b></article>;
}
