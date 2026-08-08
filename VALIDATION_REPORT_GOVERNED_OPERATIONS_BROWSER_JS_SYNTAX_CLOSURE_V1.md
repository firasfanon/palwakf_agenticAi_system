# Candidate Validation Report — Governed Operations Browser JS Syntax Closure V1

- Target mutation count: `1`
- Target: `backend/src/palwakf_local_agents/governed_operations/static/app.js`
- Known broken preimage SHA-256: `49B69C3936DE0DFC653FA2D0FD15BB848C17646B8F3DACA6B56E8249EFA9FD7A`
- Candidate postimage SHA-256: `9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041`
- Candidate source `node --check`: `PASS`
- Broken preimage `node --check`: `FAIL` as expected due to literal newline in string.
- Semantic change: exactly one replacement: `.split("<literal LF>")` → `.split("\n")`.
- Backend, router, store, API, SQLite schema, task data, review data, evidence data: `UNCHANGED`.
- Model execution: `NONE`
- Pilot execution: `NOT_EXECUTED`
