
# Manifest — Command Center Event Listener Deduplication Closure V1

## Candidate status
`CANDIDATE_PREPARED_NOT_APPLIED`

## Target mutation
`backend/src/palwakf_local_agents/command_center/static/app.js`

## Known hashes
- Preimage SHA256: `FD3A453DE80F034521A30A7AAF2E8F4087D33DBF80756BC6BA9D7576EE98803D`
- Postimage SHA256: `D83F8709428C047D9229ACD9C232BF1F552A078BBBA42B141D7FF7566006CD1E`

## Invariants
- Command Center remains read-only.
- API contract remains GET-only.
- No governed operations changes.
- No SQLite writes, model execution, Pilot execution, platform mutation, Git write, deployment, secrets, or memory writes.
