# Manifest — Governed Local Agent Core Explicit App Mount Reconciliation V1

## Purpose

Reconcile a confirmed `ALREADY_POSTIMAGE_UNMOUNTED` state: the governed local-agent source and scoped test are already present with exact candidate hashes, while `app.py` has neither the local-agent import nor the mount call.

## Exclusive project mutation

- `backend/src/palwakf_local_agents/app.py`

The installer adds exactly:

```python
from .local_agent_core import mount_local_agent_core
...
mount_local_agent_core(app, project_root=PROJECT_ROOT)
```

immediately after the existing Workspace Core import/mount anchors.

## Protected surfaces

- `local_agent_core/**`: verified only; no source write
- `workspace_core/**`: unchanged
- `governed_operations/**`: unchanged
- `command_center/**`: unchanged
- `policy_packs/**`: unchanged
- databases / SQLite: unchanged during install

## Runtime boundary

Model execution, Pilot execution, shell execution, Git write, deployment, external network, and cross-workspace access remain out of scope.
