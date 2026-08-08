export const innovationResilienceProjectIdentityV1 = {
  route: "/agent-console/innovation-resilience",
  apiPrefix: "/api/v1/operational-core",
  mode: "prepare_only",
  capabilities: [
    "innovation_review_three_alternatives",
    "context_drift_check",
    "attempt_limiter",
    "checkpoint_metadata",
    "project_design_identity",
    "deterministic_anti_similarity",
  ],
  boundaries: {
    modelInference: "none",
    shell: "blocked",
    git: "blocked",
    codeExecution: "blocked",
    selfApply: "blocked",
    vectorDb: "none",
    automaticRetry: false,
  },
} as const;
