import type { IconName } from "./components/Icon";

export type AgentRouteId =
  | "home"
  | "goal-planner"
  | "tasks"
  | "tools"
  | "projects"
  | "domain-capabilities"
  | "engineering-skills"
  | "reviews"
  | "workspaces"
  | "evidence"
  | "initial-operation"
  | "charter"
  | "state-manager"
  | "diagnostics"
  | "pilot-control";

export type AgentRouteSection = "operational" | "governance";

export interface AgentRouteDefinition {
  id: AgentRouteId;
  path: string;
  aliases?: readonly string[];
  label: string;
  description: string;
  eyebrow: string;
  icon: IconName;
  section: AgentRouteSection;
  navigation: boolean;
  uat: boolean;
}

export const AGENT_ROUTES: readonly AgentRouteDefinition[] = [
  { id: "home", path: "/agent-console", aliases: ["/agent-console/", "/agent-console/index.html"], label: "مركز العمل", description: "ابدأ من الهدف", eyebrow: "تشغيل يومي", icon: "home", section: "operational", navigation: true, uat: true },
  { id: "goal-planner", path: "/agent-console/goal-planner", label: "هدف جديد", description: "حوّل الهدف إلى خطة", eyebrow: "تخطيط", icon: "task", section: "operational", navigation: true, uat: true },
  { id: "tasks", path: "/agent-console/tasks", label: "المهام والخطط", description: "مسودات ومراجعة", eyebrow: "تشغيل", icon: "task", section: "operational", navigation: true, uat: true },
  { id: "tools", path: "/agent-console/tools", label: "المساعدون والأدوات", description: "اختر المساعد", eyebrow: "قدرات", icon: "tool", section: "operational", navigation: true, uat: true },
  { id: "projects", path: "/agent-console/projects", label: "قراءة المشروع", description: "خريطة وفهم", eyebrow: "مشروع", icon: "project", section: "operational", navigation: true, uat: true },
  { id: "domain-capabilities", path: "/agent-console/domain-capabilities", label: "مجالات التخصص", description: "وكلاء وتقنيات", eyebrow: "تخصصات", icon: "agent", section: "operational", navigation: true, uat: true },
  { id: "engineering-skills", path: "/agent-console/engineering-skills", label: "المهارات الهندسية", description: "Skills workflows", eyebrow: "مهارات", icon: "tool", section: "operational", navigation: true, uat: true },
  { id: "reviews", path: "/agent-console/reviews", label: "المراجعات", description: "قرارات بشرية", eyebrow: "مراجعة", icon: "review", section: "operational", navigation: true, uat: true },
  { id: "workspaces", path: "/agent-console/workspaces", label: "مساحة العمل", description: "السياق الحالي", eyebrow: "Workspace", icon: "workspace", section: "operational", navigation: true, uat: true },
  { id: "evidence", path: "/agent-console/evidence", label: "الأدلة", description: "سجلات وتوريث", eyebrow: "أدلة", icon: "evidence", section: "governance", navigation: true, uat: true },
  { id: "initial-operation", path: "/agent-console/initial-operation", label: "جاهزية التشغيل", description: "خريطة الجاهزية", eyebrow: "تشغيل أولي", icon: "pulse", section: "operational", navigation: false, uat: true },
  { id: "charter", path: "/agent-console/charter", label: "الميثاق", description: "الحقيقة والحدود", eyebrow: "حوكمة", icon: "shield", section: "governance", navigation: true, uat: true },
  { id: "state-manager", path: "/agent-console/state-manager", label: "حالة المشروع", description: "State Model", eyebrow: "حالة", icon: "project", section: "governance", navigation: true, uat: true },
  { id: "diagnostics", path: "/agent-console/diagnostics", label: "التشخيص", description: "Health checks", eyebrow: "تشخيص", icon: "pulse", section: "governance", navigation: true, uat: true },
  { id: "pilot-control", path: "/agent-console/pilot-control", label: "Pilot Control", description: "بوابات التشغيل", eyebrow: "تحكم", icon: "lock", section: "governance", navigation: true, uat: true },
] as const;

export const CANONICAL_UAT_ROUTES = AGENT_ROUTES.filter((route) => route.uat);
export const NAVIGATION_ROUTES = AGENT_ROUTES.filter((route) => route.navigation);

export function normalizeAgentPath(pathname: string): string {
  if (!pathname) return "/agent-console";
  const decoded = pathname.replace(/\/+$/, "");
  return decoded || "/agent-console";
}

export function resolveAgentRoute(pathname: string): AgentRouteDefinition | undefined {
  const current = normalizeAgentPath(pathname);
  return AGENT_ROUTES.find((route) =>
    route.path === current || route.aliases?.some((alias) => normalizeAgentPath(alias) === current)
  );
}

export function routeById(id: AgentRouteId): AgentRouteDefinition {
  const route = AGENT_ROUTES.find((item) => item.id === id);
  if (!route) throw new Error(`UNKNOWN_AGENT_ROUTE:${id}`);
  return route;
}
