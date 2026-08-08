# Manifest — Multi-Workspace Core + Policy Packs V1

## Candidate scope
- New `workspace_core` module, tests, documentation, policy packs, installer scripts.
- Explicit addition to `app.py`: import and one mount call only.

## Protected files
- Command Center: no mutation.
- Governed Operations: no mutation.
- Existing SQLite files: no mutation during install.

## Runtime behavior
- Registry SQLite is created on first `GET /api/v1/workspaces/health` or equivalent workspace-core read.
- Built-in workspace declarations are audit-chained in `audit/workspace_core.sqlite`.
- No workspace-specific state, evidence, memory, credentials, or migrations are initialized in V1.

## Non-goals
- No actual tool executions.
- No workspaces creation/activation.
- No local model / Pilot.
- No PalWakf legacy migration.
