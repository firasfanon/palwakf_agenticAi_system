# Security Contract — Governed Operations Foundation V1

## Allowed

- Local SQLite writes only at `audit/governed_operations.sqlite`.
- Task state writes through explicit local API lifecycle endpoints.
- Human-review trace with append-only transition events and hash chaining.
- Evidence metadata writes; no source file reading or uploads.

## Explicitly prohibited

- Model/Ollama/provider calls.
- Pilot execution.
- Platform mutation.
- External database access.
- Git write, deployment, secret access, memory writes.
- Arbitrary filesystem browsing or source-content ingestion.

## Existing Command Center invariant

`/command-center` and `/api/v1/local-agents/*` remain read-only and must not be used as a write surface.

## Identity limitation

Actor IDs provide audit attribution only; V1 does not implement user authentication, password handling, tokens, or RBAC.
