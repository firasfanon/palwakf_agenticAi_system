export const OPERATIONAL_CORE_6_IN_1_FOUNDATION_V1 = Object.freeze({
  route: "/agent-console/operational-core",
  apiPrefix: "/api/v1/operational-core",
  capabilities: [
    "OPERATIONAL_CORE_VERTICAL_SLICE_V1_NO_EXECUTION",
    "LOCAL_STATE_STORE_V1_JSONL_PROJECT_STATE",
    "CODEBASE_SYMBOL_ROUTE_COMPONENT_INDEX_V1_READ_ONLY",
    "GOVERNED_READ_ONLY_TOOL_RUNTIME_V1",
    "STANDING_RULES_REGISTRY_V1",
    "LOCAL_MODEL_RUNTIME_READINESS_GATE_V1",
  ],
  runtimeBoundaries: {
    modelInference: false,
    shell: false,
    git: false,
    codeExecution: false,
    selfApply: false,
    localStateWrite: "runtime_state/operational_core_v1 only",
  },
});
