# Manifest — Workspace Core Operational UI/UX Language Closure V1

## Candidate role
UI/UX and language closure for the already-mounted Multi-Workspace Core V1.

## Exact target mutation scope
- `backend/src/palwakf_local_agents/workspace_core/static/index.html`
- `backend/src/palwakf_local_agents/workspace_core/static/styles.css`
- `backend/src/palwakf_local_agents/workspace_core/static/app.js`
- `backend/tests/test_workspace_core.py`
- Three documentation files under `docs/`.

## Protected surfaces
- `app.py`: unchanged.
- `workspace_core/store.py`, `router.py`, `contracts.py`, `policy.py`: unchanged.
- `policy_packs/`: unchanged.
- Command Center: unchanged.
- Governed Operations: unchanged.
- SQLite: no write during installer execution.

## Runtime posture
- Existing GET-only API remains unchanged.
- UI reads existing GET endpoints only.
- No execution, create, update, delete, policy mutation, model execution, or Pilot execution.
