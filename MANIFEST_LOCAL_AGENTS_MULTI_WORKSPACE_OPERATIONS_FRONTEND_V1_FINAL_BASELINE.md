# Manifest — Local Agents Multi-Workspace Operations Frontend V1 Final Baseline Carrier

- **Package ID:** `PALWAKF_LOCAL_AGENTS_MEGA_BATCH_LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_FINAL_BASELINE_CARRIER_REBUILD_CANDIDATE`
- **Phase:** `FRONTEND_DISCOVERY_AND_DESIGN_BASELINE_ONLY`
- **Execution mode:** `Syntax -> Runtime Fixture Self-Test -> Actual Baseline -> Planning WhatIf`

## Required design outcomes

- Discover the actual frontend delivery mode before selecting or replacing any framework.
- Inventory static roots, frontend assets, API route decorators, frontend `fetch()` calls, and detected framework manifests/configuration.
- Bind later implementation to the real `app.py` hash discovered during baseline.
- Produce UI planning scope for Command Center, Workspaces, Tasks, Projects, Research, Evidence, Reviews, Tools, Pilot Control, and Diagnostics.

## Governing UI contract

- Arabic-first and RTL-ready.
- Default-deny state is visible and explained.
- Actor scope, workspace scope, and commercial client scope must be represented by the eventual UI.
- No fake successful data.
- No hard-coded actor token.
- No token persistence.
- No cross-workspace selector leakage.
- No cross-client commercial data exposure.
- No model execution from the frontend.

## Explicit exclusions

- No static asset mutation.
- No app entrypoint mutation.
- No API contract mutation.
- No service start.
- No model prompt or Ollama invocation.
- No Shell, Git, deployment, or external network activity.
