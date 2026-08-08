# UAT — Governed Operations Foundation V1

## Functional

1. `GET /api/v1/governed-operations/health` shows SQLite-only local state and disabled execution.
2. Create a draft with a valid `Idempotency-Key`.
3. Repeat the exact request with the same key; the same task ID must return as a replay.
4. Attempt review before `under_review`; expect 409.
5. Submit → start review → approve; verify `execution_state=NOT_EXECUTED`.
6. Verify transition events preserve previous_hash → event_hash chain.
7. Add Evidence metadata with `trust_level=working`; UI shows Arabic `قيد المراجعة` while raw status remains available.
8. `POST /api/v1/governed-operations/execute` returns 404 because no dispatcher exists.

## Regression

1. Command Center Static Gate remains PASS.
2. Existing Command Center test remains PASS.
3. `/api/v1/local-agents/*` remains GET-only.
4. `POST /api/v1/local-agents/dashboard` remains 405.

## Browser

- `/operations` loads in Arabic RTL.
- Create task, route it to review, make a decision, then archive it.
- No execution control exists anywhere in UI.
