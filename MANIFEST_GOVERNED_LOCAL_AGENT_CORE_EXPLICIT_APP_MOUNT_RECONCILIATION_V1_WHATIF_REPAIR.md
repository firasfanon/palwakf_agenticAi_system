# Manifest — Governed Local Agent Core Explicit App Mount Reconciliation V1: WhatIf Repair

## Purpose

This is a **package-side installer repair** for the already-approved reconciliation package. It enables a true `-WhatIf` path without `-Apply`.

## Confirmed project state

- `local_agent_core/**` and its scoped test are already present and must be verified, not copied.
- `app.py` remains the sole project mutation when a later explicit `-Apply` is authorized.
- Preflight state must be `ALREADY_POSTIMAGE_UNMOUNTED` before `-WhatIf` or `-Apply`.

## Exclusive package change

- `scripts/Install-GovernedLocalAgentCoreExplicitAppMountReconciliationV1.ps1`
- `scripts/Test-GovernedLocalAgentCoreExplicitAppMountReconciliationV1CandidateSyntax.ps1`
- Package documentation and inventory only.

## True WhatIf contract

`-WhatIf` may run without `-Apply`. It:

1. Verifies the preflight manifest and all source hashes.
2. Verifies the app anchors remain `workspace=1/1`, `local_agent=0/0`.
3. Computes a predicted `app.py` postimage hash in memory.
4. Emits the predicted anchor counts (`1/1/1/1`).
5. Writes no project file, no backup, and no SQLite state.

## Actual Apply contract

Actual project mutation still requires `-Apply` and changes `backend/src/palwakf_local_agents/app.py` only.

## Protected surfaces

- `local_agent_core/**`: verified only; no source write.
- `workspace_core/**`: unchanged.
- `governed_operations/**`: unchanged.
- `command_center/**`: unchanged.
- `policy_packs/**`: unchanged.
- SQLite/databases: unchanged during WhatIf and install.

## Runtime boundary

Model execution, Pilot execution, shell execution, Git write, deployment, external network, and cross-workspace access are out of scope.
