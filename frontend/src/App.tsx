import type { ReactNode } from "react";
import { BoundaryPanel } from "./components/OperationalPanels";
import { Layout } from "./components/Layout";
import { EngineeringSkillsRegistryPage, SpecializedAgentCatalogPage } from "./pages/CapabilityPages";
import { ProjectRealityCharter, ProjectStateManager } from "./pages/GovernancePages";
import { InitialOperationReadinessPage } from "./pages/InitialOperationPage";
import {
  Diagnostics,
  OperationalEvidence,
  OperationalGoalPlanner,
  OperationalHome,
  OperationalProjects,
  OperationalReviews,
  OperationalTasks,
  OperationalTools,
  OperationalWorkspaces,
  PilotControl,
} from "./pages/OperationalPages";
import { resolveAgentRoute, type AgentRouteId } from "./routes";

export function App() {
  const route = resolveAgentRoute(location.pathname);
  if (!route) {
    return <Layout eyebrow="مسار غير مسجل" title="الصفحة غير موجودة">
      <BoundaryPanel title="لا يوجد انتقال" detail="ارجع إلى مركز العمل أو أحد المسارات المسجلة."/>
    </Layout>;
  }

  const renderers: Record<AgentRouteId, () => ReactNode> = {
    "home": () => <OperationalHome/>,
    "workspaces": () => <OperationalWorkspaces/>,
    "tasks": () => <OperationalTasks/>,
    "projects": () => <OperationalProjects/>,
    "domain-capabilities": () => <SpecializedAgentCatalogPage/>,
    "engineering-skills": () => <EngineeringSkillsRegistryPage/>,
    "goal-planner": () => <OperationalGoalPlanner/>,
    "tools": () => <OperationalTools/>,
    "reviews": () => <OperationalReviews/>,
    "evidence": () => <OperationalEvidence/>,
    "initial-operation": () => <InitialOperationReadinessPage/>,
    "charter": () => <ProjectRealityCharter/>,
    "state-manager": () => <ProjectStateManager/>,
    "diagnostics": () => <Diagnostics/>,
    "pilot-control": () => <PilotControl/>,
  };

  return renderers[route.id]();
}
