# Manifest — Multi-Workspace Core Explicit App Mount Reconciliation V1

## Purpose
This candidate reconciles a partial/staged Multi-Workspace Core installation where all workspace source, policy, test, and documentation files already match the accepted V1 Candidate, but `app.py` does not yet import or mount `workspace_core`.

## Scope
- **Single mutable target:** `backend/src/palwakf_local_agents/app.py`
- Adds exactly one import:
  `from .workspace_core import mount_workspace_core`
- Adds exactly one mount:
  `mount_workspace_core(app, project_root=PROJECT_ROOT)`

## Preconditions
1. The 17 Multi-Workspace Core V1 files match the source-hash contract.
2. `app.py` contains exactly one governed-operations import and mount anchor.
3. `app.py` contains no workspace-core import or mount.
4. No runtime process is actively serving stale source during the actual apply.

## Non-goals
- Does not alter Workspace Core source, policy packs, tests, docs, Command Center, or Governed Operations.
- Does not initialize workspace SQLite, migrate legacy data, invoke models, execute Pilot, access a platform, database, Git, deployment, secrets, or memory.

## Safety posture
`MODEL_EXECUTION=NONE`  
`PILOT_EXECUTION=NOT_EXECUTED`  
`LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL`  
`LEGACY_MIGRATION=NONE`
