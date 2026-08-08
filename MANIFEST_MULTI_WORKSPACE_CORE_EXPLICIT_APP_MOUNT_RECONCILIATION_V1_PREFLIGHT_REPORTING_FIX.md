# Manifest — Multi-Workspace Core Explicit App Mount Reconciliation V1: Preflight Reporting Fix

## Candidate identity

- **Candidate ID:** `MULTI_WORKSPACE_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_PREFLIGHT_REPORTING_FIX`
- **Status:** `CANDIDATE_PREPARED_NOT_APPLIED`
- **Purpose:** Correct a PowerShell 5.1 reporting defect in the reconciliation preflight. The previous script used `PSObject.Properties.Count` directly, which emitted a sequence of `1` values in the supplied run instead of one scalar count. This candidate materializes note-properties into an array and emits scalar counts deterministically.

## Scope

- Changes **only package-side validation scripts and package documentation**.
- The project target is not modified by syntax/preflight validation.
- The embedded app-mount installer is byte-for-byte unchanged from the preceding reconciliation candidate.

## Explicit non-scope

```text
NO_APP_PY_MUTATION_DURING_PREFLIGHT
NO_WORKSPACE_CORE_SOURCE_MUTATION
NO_POLICY_PACKS_MUTATION
NO_COMMAND_CENTER_MUTATION
NO_GOVERNED_OPERATIONS_MUTATION
NO_SQLITE_WRITE
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_PLATFORM_MUTATION
```

## Apply posture

This is not an application authorization. A future explicit apply authorization remains required before using the included app.py installer.
