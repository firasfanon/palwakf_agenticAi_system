# Command Center V1 — Security Contract

## Endpoint policy
Only `GET` endpoints are registered. No endpoint exists for start, approve, archive, write memory, shell, SQL, model execution, or external integrations.

## Allowlisted sources
- `tasks/inbox`
- `tasks/approved`
- `tasks/archived`
- `audit/human_reviews`
- `output/evidence_manifests`
- `output/evals`
- `reference_sources/approved`
- fixed known root governance filenames only

## Denied behavior
- arbitrary file paths and traversal;
- `.env`, credentials and secrets;
- raw backup browsing;
- subprocess invocation;
- Ollama/model invocation;
- network/database/Git/deployment/memory write.

## Response markers
Every safety-bearing endpoint returns or displays:
`MODEL_EXECUTION=NONE`, `PILOT_EXECUTION=NOT_EXECUTED`, `PLATFORM_MUTATION=NONE`, `DATABASE_ACCESS=NONE`, `GIT_WRITE=NONE`, `DEPLOYMENT=NONE`, `SECRETS_ACCESS=NONE`, `MEMORY_WRITE=NONE`.
