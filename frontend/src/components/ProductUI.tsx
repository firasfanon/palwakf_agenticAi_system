import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export function PageLead({ icon, eyebrow, title, detail, actions }: {
  icon: IconName;
  eyebrow: string;
  title: string;
  detail?: string;
  actions?: ReactNode;
}) {
  return <section className="p4-page-lead">
    <span className="p4-page-lead-icon"><Icon name={icon} size={24}/></span>
    <div className="p4-page-lead-copy"><p>{eyebrow}</p><h2>{title}</h2>{detail && <span>{detail}</span>}</div>
    {actions && <div className="p4-page-lead-actions">{actions}</div>}
  </section>;
}

export function ProgressiveDisclosure({ title, summary, children, defaultOpen = false }: {
  title: string;
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return <details className="p4-disclosure" open={defaultOpen}>
    <summary><span><strong>{title}</strong><small>{summary}</small></span><b aria-hidden="true">+</b></summary>
    <div className="p4-disclosure-body">{children}</div>
  </details>;
}

export function DataState({ kind, title, detail, children }: {
  kind: "loading" | "empty" | "error" | "ready";
  title: string;
  detail?: string;
  children?: ReactNode;
}) {
  if (kind === "ready") return <>{children}</>;
  return <section className={`p4-data-state state-${kind}`} role={kind === "error" ? "alert" : "status"} aria-live="polite">
    <strong>{title}</strong>{detail && <span>{detail}</span>}
  </section>;
}
