# Manifest — Governed Operations Workspace Scoping V1

## Authorized design objective
Bind governed local operations to a mandatory workspace identifier and an evaluated policy pack while keeping legacy V1 state separate.

## Candidate mutation scope
- `backend/src/palwakf_local_agents/governed_operations/` only
- `backend/tests/test_governed_operations_workspace_scoping.py` only

## Explicitly unchanged
- `app.py`
- `workspace_core/`
- `policy_packs/`
- `command_center/`
- `governed_operations` legacy SQLite data
- Platform, external DB, Git, deployment, secrets, memory and model/Pilot execution

## API contract
- `GET /api/v1/governed-operations/health`
- `GET /api/v1/governed-operations/workspaces`
- `GET|POST /api/v1/governed-operations/workspaces/{workspace_id}/...`
- `GET /api/v1/governed-operations/legacy/status`

No unscoped write route is part of the V1 scoped contract.

## Storage contract
`workspaces/<workspace_id>/governed_operations.sqlite` is created only after an explicit local POST action. No migration from `audit/governed_operations.sqlite` occurs.

## Acceptance gates
1. Candidate syntax and static contract pass.
2. Preflight validates Workspace Core and all four policy packs, and emits a fresh preimage manifest.
3. WhatIf is clean.
4. Explicit Apply must be separately authorized.
5. Runtime UAT must prove cross-workspace negative tests and `NOT_EXECUTED` after approval.
