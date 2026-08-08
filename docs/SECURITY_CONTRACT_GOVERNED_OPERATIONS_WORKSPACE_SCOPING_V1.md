# Security Contract

- `workspace_id` path-bound and identifier-validated.
- Pydantic payloads use `extra=forbid`; body-based workspace reassignment is rejected.
- Per-workspace SQLite file prevents cross-workspace query joins by construction.
- Existing legacy V1 operations state remains separate and not migrated.
- `execution_state=NOT_EXECUTED` is immutable in this batch.
- No `execute`, `dispatch`, model, Pilot, external network, platform mutation, deployment, secrets or Git write route exists.
- Approval remains a governance state only and never becomes execution.
