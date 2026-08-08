# Manifest — Frontend V1 Baseline Carrier Empty-Collection Binding Repair

- **Package ID:** `PALWAKF_LOCAL_AGENTS_FRONTEND_V1_BASELINE_CARRIER_EMPTY_COLLECTION_BINDING_REPAIR_CANDIDATE`
- **Phase:** `FRONTEND_DISCOVERY_AND_DESIGN_BASELINE_ONLY`
- **Repair scope:** `EMPTY_COLLECTION_BINDING_ONLY`
- **Execution mode:** `Syntax -> Runtime Fixture Self-Test -> Actual Baseline -> Planning WhatIf`

## Repair binding

The baseline inventory appender must accept an initially empty `ArrayList` on Windows PowerShell 5.1. The target is validated explicitly as `System.Collections.IList`, rather than being bound as a mandatory collection parameter.

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
