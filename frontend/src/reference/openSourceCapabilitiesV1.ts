export type OpenSourceCapabilityDecision =
  | "high_priority_read_only_candidate"
  | "high_priority_local_telemetry_candidate"
  | "accepted_candidate_runtime_blocked"
  | "deferred_accepted_candidate"
  | "architecture_deferred"
  | "optional_later_license_boundary_required"
  | "license_review_required"
  | "reference_only_current_phase";

export interface OpenSourceCapabilitySummary {
  id: string;
  name: string;
  licenseClassification: string;
  capabilityClass: string;
  decision: OpenSourceCapabilityDecision;
  integrationMode: "safe_adapter_contract_only" | "registry_reference_only";
}

export const openSourceCapabilityV1Boundary = Object.freeze({
  mode: "read_only_census_and_contracts_only",
  download: false,
  install: false,
  toolExecution: false,
  scannerExecution: false,
  networkRuntime: false,
  sourceMutationByTool: false,
});
