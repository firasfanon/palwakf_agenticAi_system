# Error Record — Rev C Static Gate Precision Failure

## Observed Rev C outcome
`VALIDATION_FAILURE_COUNT=2`
- `TASK_WRITE_CALL|...read_only_store.py`
- `TASK_WRITE_CALL|...static/app.js`

## Corroborating runtime evidence
- Unit tests passed: 4/4.
- Route probe passed: 10 Command Center routes, GET-only.
- System health: `READ_ONLY_READY`.
- Active approved task remains one, and `PILOT_EXECUTION=NOT_EXECUTED`.

## Root cause
Rev C regex treated generic `.replace(...)` as a filesystem write.
This matches normal non-mutating string normalization and UI formatting.

## Corrective action
Rev D removes generic `.replace(...)` from filesystem-write detection, keeps `os.replace(...)` prohibited,
separates Python filesystem checks from web-source HTTP method checks, and adds 3 deterministic evals.
