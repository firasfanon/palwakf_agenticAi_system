# Security Contract — Command Center V1.2 Rev C

## Scope
Static-gate repair only. No production/runtime behavior is altered.

## Allowed mutation
- Replace only `scripts/Test-CommandCenterV1RevBStatic.ps1`.
- Create an exact preimage copy and JSON manifest under `backups/`.

## Forbidden mutation
- No changes to `app.py`.
- No changes to `backend/src/palwakf_local_agents/command_center/`.
- No task/review/evidence/reference changes.
- No dependency installation.
- No model, pilot, database, platform, Git, deployment, secrets, or memory activity.

## Scan contract
The repaired gate scans only readable source files with extensions `.py`, `.js`, `.html`, `.css`.
It excludes `__pycache__` directories and `.pyc` bytecode to prevent binary false positives.
