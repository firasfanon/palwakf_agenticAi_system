# Baselines and System Contracts V2

## Baseline
A baseline records an accepted state, verification evidence, remaining risks, and rollback reference.
It is not an informal status message.

## System contract
A system contract identifies an interface that cannot be changed casually:
- API,
- database,
- authorization,
- environment variable,
- storage,
- navigation,
- integration,
- agent-tool boundary.

## Current project-specific boundary
`palwakf_local_agents` may read imported reference snapshots under controlled scope in a future runner.
It must not mutate the PalWakf platform as a side effect.
