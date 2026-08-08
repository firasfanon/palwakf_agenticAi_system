export const goalPlannerToolSelectionBindingV1 = {
  id: "QUALITY_ACCEPTED_TOOLS_GOAL_PLANNER_SELECTION_BINDING_V1",
  contractVersion: "1.1.0",
  route: "/agent-console/goal-planner-tool-selection",
  apiPrefix: "/api/v1/operational-core/planner-tool-selection",
  mode: "ADVISORY_ONLY_NO_EXECUTION",
  reconciliation: {
    nestedMapContainers: ["scorecards", "baselines", "quarantines"],
    canonicalAliases: {
      native_code_index_contract: "native-code-index",
      local_telemetry_contract: "local-telemetry",
      tree_sitter: "tree-sitter",
    },
    automaticQualityAcceptance: false,
  },
  qualityStates: {
    QUALITY_ACCEPTED: "SELECTABLE",
    PASS_WITH_LIMITATIONS: "SELECTABLE_WITH_LIMITATIONS",
    HUMAN_REVIEW_REQUIRED: "HUMAN_REVIEW_REQUIRED",
    UNASSESSED: "BLOCKED_UNASSESSED",
    QUALITY_FAILED: "BLOCKED_QUALITY_FAILED",
    QUARANTINED: "FORBIDDEN_QUARANTINED",
    REVALIDATION_REQUIRED: "BLOCKED_REVALIDATION_REQUIRED",
  },
} as const;
