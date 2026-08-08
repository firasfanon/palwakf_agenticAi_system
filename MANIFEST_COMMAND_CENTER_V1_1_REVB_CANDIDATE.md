# Manifest — Command Center V1.1 Rev B Candidate

## State
`CANDIDATE_PREPARED_NOT_APPLIED`

## Scope
Arabic RTL Command Center integration, read-only API and static assets only.

## Exact target locations
- `backend/src/palwakf_local_agents/command_center/*`
- `backend/tests/test_command_center_read_only.py`
- `backend/src/palwakf_local_agents/app.py` (explicit mount patch only)
- `scripts/Test-CommandCenterV1RevBStatic.ps1`
- documentation files listed in the installer plan.

## Explicitly unchanged
- `command_center/` at project root (legacy V1 candidate artifact).
- core task lifecycle.
- 11-line output contract.
- approved pilot task and its execution state.

## Safety markers
`MODEL_EXECUTION=NONE`
`PILOT_EXECUTION=NOT_EXECUTED`
`PLATFORM_MUTATION=NONE`
`DATABASE_ACCESS=NONE`
`GIT_WRITE=NONE`
`DEPLOYMENT=NONE`
`SECRETS_ACCESS=NONE`
`MEMORY_WRITE=NONE`
