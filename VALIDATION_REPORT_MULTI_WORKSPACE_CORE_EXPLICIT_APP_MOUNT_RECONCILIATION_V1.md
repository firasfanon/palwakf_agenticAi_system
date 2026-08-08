# Validation Report — Candidate

## Candidate validation performed
- Candidate package contains only validation scripts, source-hash contract, manifest, and application guidance.
- Installer target scope is fixed to `backend/src/palwakf_local_agents/app.py`.
- Installer requires exact one-time governed-operations anchors, and rejects existing workspace-core import or mount.
- Installer uses `SupportsShouldProcess`; `-WhatIf` does not write project files or backups.
- Source-hash contract verifies all 17 reconciled Workspace Core V1 files before actual patching.

## Runtime validation deferred
HTTP and browser UAT are intentionally deferred until explicit Apply authorization and a separate post-apply verification gate.
