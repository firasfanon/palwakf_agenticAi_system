# Manifest — Governed Local Agent Core V1

## Intended source mutation

- New: `backend/src/palwakf_local_agents/local_agent_core/**`
- New: `backend/tests/test_governed_local_agent_core.py`
- One explicit `app.py` import/mount: `mount_local_agent_core`

## Protected surfaces

- `workspace_core/**` unchanged
- `governed_operations/**` unchanged
- `command_center/**` unchanged
- `policy_packs/**` unchanged
- No migration of existing data or legacy state

## Runtime boundary

`LOCAL_DETERMINISTIC_PREPARE_ONLY`; model and pilot execution remain disabled.

## Candidate repair provenance

Use this `PREFLIGHT_RUNTIME_REPAIR_CANDIDATE` package instead of the original V1 Candidate. It repairs package-side PowerShell Preflight semantics only; the intended project mutation and backend postimage are unchanged.
