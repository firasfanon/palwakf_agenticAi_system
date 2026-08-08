# Security Contract — Multi-Workspace Core + Policy Packs V1

- `NO_CROSS_WORKSPACE_READ_WRITE_TOOL_MEMORY_OR_AUDIT_ACCESS`
- `NO_WORKSPACE_STORAGE_INITIALIZATION_DURING_INSTALL`
- `NO_LEGACY_GOVERNED_OPERATIONS_MIGRATION`
- `NO_MODEL_EXECUTION`
- `NO_PILOT_EXECUTION`
- `NO_PLATFORM_MUTATION`
- `NO_EXTERNAL_DATABASE_ACCESS`
- `NO_GIT_WRITE`
- `NO_DEPLOYMENT`
- `NO_SECRETS_ACCESS`
- `NO_MEMORY_WRITE`

Policy packs are descriptive and enforced only by the Core surface in this batch. Tool invocation and workspace state binding require later explicit authorization.
