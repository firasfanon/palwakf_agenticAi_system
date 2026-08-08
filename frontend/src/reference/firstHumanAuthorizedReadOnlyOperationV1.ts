export const firstHumanAuthorizedReadOnlyOperationV1 = {
  route: '/agent-console/first-read-only-operation',
  apiPrefix: '/api/v1/operational-core/first-read-only-operation',
  contractId: 'FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_V1',
  operationType: 'READ_ONLY_CODEBASE_INDEX_AND_STRUCTURE_REPORT',
  toolId: 'native-code-index',
  humanAuthority: 'required_per_operation',
  sourceMutation: 'blocked',
  productionExecution: 'not_authorized',
} as const;
