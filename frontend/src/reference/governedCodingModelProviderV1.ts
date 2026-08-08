export const governedCodingModelProviderV1 = {
  contractId: "GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1",
  route: "/agent-console/coding-model",
  apiPrefix: "/api/v1/operational-core/coding-model",
  providerModes: ["disabled", "ollama", "openai_compatible"] as const,
  boundaries: {
    modelExecution: "EXPLICIT_HUMAN_AUTHORIZATION_ONLY",
    providerNetwork: "LOOPBACK_ONLY",
    realSourceWrite: "NONE",
    sourceApply: "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION",
    shell: "NONE",
    git: "NONE",
    databaseWrite: "NONE",
    selfApply: "BLOCKED",
  },
} as const;
