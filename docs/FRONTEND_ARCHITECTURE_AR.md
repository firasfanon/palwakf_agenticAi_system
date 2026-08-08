# Frontend Architecture Baseline — Repair Binding Integrity

## Scope

This carrier preserves the existing discovery design. It changes only the baseline inventory append binding so an initially empty inventory list can be used on Windows PowerShell 5.1.

## Discovery, not framework replacement

The baseline identifies the current delivery surface from the project itself. A static root is not permission to replace the frontend with a framework. A discovered package or framework configuration is evidence only.

## Baseline dimensions

1. `static_roots`
2. `assets`
3. `route_inventory`
4. `fetch_inventory`
5. `frontend_framework_inventory`

## Execution boundary

No project source mutation, no service start, no prompt/model execution, no network, no Git, and no deployment.
