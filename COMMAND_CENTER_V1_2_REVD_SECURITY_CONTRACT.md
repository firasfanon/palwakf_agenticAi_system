# Security Contract — Command Center V1.2 Rev D

## Allowed mutation
- Replace only `scripts/Test-CommandCenterV1RevBStatic.ps1`.
- Create exact preimage backup plus manifest beneath `backups/`.

## Forbidden mutation
- No change to `app.py`.
- No change to `backend/src/palwakf_local_agents/command_center/*`.
- No change to tests, tasks, audits, output evidence, references, dependencies, or runtime configuration.
- No model, pilot, platform, database, Git, deployment, secrets, or memory activity.

## Scan semantics
- Generic string `.replace()` is not a filesystem mutation.
- `os.replace(...)` remains prohibited.
- Filesystem mutation detection runs only in Python Command Center source.
- Non-GET HTTP method declarations remain prohibited in web source.
