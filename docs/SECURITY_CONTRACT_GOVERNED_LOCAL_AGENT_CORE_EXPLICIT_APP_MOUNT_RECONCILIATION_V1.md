# Security Contract

- Trust source: `CANDIDATE_SOURCE_POSTIMAGE_SHA256.json` validates the existing 11 local-agent source/test files before any application action.
- Allowed mutation: only one `app.py` import and one `app.py` mount after the pre-existing Workspace Core anchors.
- Reject on: missing or hash-conflicting source, anchor count drift, app preimage drift, missing `.venv` during post-apply AST verification.
- Backup: `app.py` plus install preimage manifest only.
- Runtime: no model execution, Pilot, shell, Git write, database write, deploy, network call, or cross-workspace access.
