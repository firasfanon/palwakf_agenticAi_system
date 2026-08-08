# Command Center V1.1 Rev B — Security Contract

## Read-only contract
- Allowlisted data roots only:
  `tasks/inbox`, `tasks/approved`, `tasks/archived`, `audit/human_reviews`,
  `output/evidence_manifests`, `output/evals`, `reference_sources/approved`.
- Task id validates against a strict identifier regular expression.
- Project-relative metadata only. No arbitrary file browser.
- Static assets are bundled with the Python package.
- Command Center routes are GET-only.

## Explicit exclusions
- `POST/PUT/PATCH/DELETE` routes under `/api/v1/local-agents`.
- subprocess or shell execution.
- model/Ollama clients.
- external network calls.
- database clients.
- Git/deployment clients.
- environment/secret loading.
- memory/task/review/archive writes.

## Integration scope
Only `backend/src/palwakf_local_agents/app.py` is patched, to register the Command Center mount. Core task lifecycle logic and the 11-line model output contract are not changed.
