# Changelog

- Adds a separate governed operations module and local SQLite state.
- Adds task lifecycle state machine with idempotent creation.
- Adds human review and hash-linked transitions.
- Adds evidence metadata lifecycle with Arabic display status.
- Adds separate `/operations` workbench UI.
- Does not modify Command Center read-only API or static UI.
- Does not add model, Pilot, platform, external DB, Git, deployment, secret, or memory operations.
