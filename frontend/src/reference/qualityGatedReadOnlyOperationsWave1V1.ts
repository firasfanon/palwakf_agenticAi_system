export const qualityGatedReadOnlyOperationsWave1V1 = Object.freeze({
  mainRoute: "/agent-console/operations",
  governanceRoutes: [
    "/agent-console/operations/governance",
    "/agent-console/operations/manifests",
    "/agent-console/operations/evidence",
  ],
  apiPrefix: "/api/v1/operational-core/operations-wave1",
  userExperience: "operational_ux_first",
  governancePlacement: "subpages",
  modelInference: "none",
  shell: false,
  git: false,
  networkRuntime: false,
  sourceWrite: false,
  automaticRetry: false,
  humanApprovalRequired: true,
  humanResultReviewRequired: true,
});
