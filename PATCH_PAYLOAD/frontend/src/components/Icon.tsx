import type { ReactNode } from "react";

export type IconName =
  | "home" | "workspace" | "task" | "project" | "evidence" | "review"
  | "tool" | "pulse" | "lock" | "shield" | "agent" | "arrow" | "menu" | "close";

const paths: Record<IconName, ReactNode> = {
  home: <><path d="M3.5 10.4 12 3l8.5 7.4"/><path d="M5.7 9.7v10h12.6v-10"/><path d="M9.3 19.7v-5.8h5.4v5.8"/></>,
  workspace: <><rect x="3.5" y="5" width="17" height="13.5" rx="2.3"/><path d="M3.5 9h17M8 3.5v3M16 3.5v3"/></>,
  task: <><rect x="4" y="3.5" width="16" height="17" rx="2.4"/><path d="m8 9 1.6 1.7L13 7.3M8 15h8"/></>,
  project: <><path d="M3.5 7.2h6l1.5 1.8h9.5v10.5H3.5z"/><path d="M3.5 7.2V5.6A2.1 2.1 0 0 1 5.6 3.5h3.1l1.4 1.7"/></>,
  evidence: <><path d="M6 3.5h9l3 3v14H6z"/><path d="M15 3.5v3h3M9 11h6M9 15h6"/></>,
  review: <><path d="M12 21a8.7 8.7 0 1 0 0-17.4A8.7 8.7 0 0 0 12 21Z"/><path d="m8.3 12.1 2.2 2.2 5.3-5.5"/></>,
  tool: <><path d="m13.3 6.1 4.6 4.6M14.7 3.6a4.1 4.1 0 0 0-4.8 5.9L3.7 15.7a2.2 2.2 0 0 0 3.1 3.1l6.2-6.2a4.1 4.1 0 0 0 5.9-4.8l-2.8 2.1-3.2-3.2z"/></>,
  pulse: <><path d="M3.5 12h3.2l1.8-4.3 3.2 9 2.2-5h6.6"/></>,
  lock: <><rect x="5" y="10" width="14" height="10.5" rx="2.2"/><path d="M8 10V7.7A4 4 0 0 1 12 3.8a4 4 0 0 1 4 3.9V10"/></>,
  shield: <><path d="M12 3.3 19 6v5.3c0 4.3-3 7.8-7 9.4-4-1.6-7-5.1-7-9.4V6z"/><path d="m8.7 12 2.1 2.1 4.6-4.8"/></>,
  agent: <><rect x="4" y="6" width="16" height="13" rx="3"/><path d="M12 3v3M8.4 12h.1M15.5 12h.1M9 15.5c1.6.8 4.3.8 6 0"/></>,
  arrow: <><path d="M5 12h13M13.5 6.5 19 12l-5.5 5.5"/></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
};

export function Icon({ name, size = 20, label }: { name: IconName; size?: number; label?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden={label ? undefined : true} role={label ? "img" : undefined} aria-label={label}>{paths[name]}</svg>;
}
