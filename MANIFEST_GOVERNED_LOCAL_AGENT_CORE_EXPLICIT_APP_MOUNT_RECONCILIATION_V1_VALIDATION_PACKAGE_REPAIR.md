# Manifest — Governed Local Agent Core Explicit App Mount Reconciliation V1: Validation Package Repair

## Package identity

```text
BATCH=GOVERNED_LOCAL_AGENT_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_VALIDATION_PACKAGE_REPAIR
TYPE=PACKAGE_SIDE_VALIDATION_REPAIR
PROJECT_POSTIMAGE_CHANGE=NONE
```

## Confirmed prior state

- `local_agent_core/**` and `test_governed_local_agent_core.py` are already present in the project and exactly match the approved postimage.
- `app.py` remains unmapped for `local_agent_core` before a future explicit Apply.
- The preceding WhatIf repair package completed Preflight and true WhatIf successfully, but its Candidate Syntax gate referenced stale root-document names and failed before its runtime checks.

## Exclusive repair scope

Only the package-side Candidate Syntax validation contract is repaired:

- Required file names are aligned with this package's actual Manifest, Apply Guide, and Validation Report.
- Package inventory is regenerated over the exact files shipped.
- The preflight and installer logic are copied unchanged from the already-proven WhatIf repair package.

## Non-goals

- No mutation of `backend/**` within the project.
- No changes to `app.py` during Candidate Syntax, Preflight, or WhatIf.
- No `local_agent_core` source copy or overwrite.
- No SQLite creation or write.
- No model, Pilot, shell, Git, deployment, network, or memory execution.

## Expected Windows gates

1. Candidate Syntax passes.
2. Preflight confirms `ALREADY_POSTIMAGE_UNMOUNTED` and emits a manifest.
3. True WhatIf completes without `-Apply` and predicts only `app.py` import/mount state.
4. Actual Apply remains separately authorized.
