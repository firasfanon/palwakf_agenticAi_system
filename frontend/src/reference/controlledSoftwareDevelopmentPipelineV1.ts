export const controlledSoftwareDevelopmentPipelineV1 = {
  route: "/agent-console/development-pipeline",
  apiPrefix: "/api/v1/operational-core/development-pipeline",
  contractId: "CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_V1",
  firstCandidateProfile: "READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1",
  candidateWorkspaceWrite: "allowed_local_only",
  realSourceWrite: "blocked",
  sourceApplyEndpoint: "absent_by_design_v1",
  modelExecution: "none",
  controlledTestRunner: "direct_argv_python_allowlist_only",
  humanAuthority: "required",
} as const;
