# Security Contract

1. All writes are local SQLite only and occur only after an explicit human UI/API request.
2. No model invocation, pilot execution, platform mutation, external database, Git, deployment, secrets, or memory writes.
3. No /execute or /dispatch route is provided.
4. Approval requires local human-review attestation, expected task version, and all declared evidence categories.
5. Actor identity is local attribution only, not authentication or RBAC.
6. Command Center remains outside this batch and must not be mutated.
