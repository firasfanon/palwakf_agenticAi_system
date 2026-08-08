# UAT — Multi-Workspace Core + Policy Packs V1

## Technical Gates
- Candidate syntax and package integrity.
- Core tests: workspace enumeration, policy separation, negative cross-workspace checks, audit integrity, absence of execution routes.
- Command Center and Governed Operations existing tests remain green.

## Browser UAT
- `/workspaces` renders all four declared spaces.
- Each workspace displays its bound policy and readiness.
- PalWakf shows government strict policy and legacy not migrated.
- No create/execute/dispatch controls appear.

## Explicitly excluded
- Creating new workspaces.
- Activating any workspace.
- Workspace storage initialization.
- Legacy migration.
- Tools, model, Pilot, bridge, Git, deployment, secrets, memory writes.
