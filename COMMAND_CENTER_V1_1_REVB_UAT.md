# Command Center V1.1 Rev B — UAT

1. Package syntax gate passes.
2. Preflight reports:
   - package-native target location;
   - legacy root module present but unchanged;
   - no pre-existing mount.
3. Installer WhatIf reports:
   - `INSTALL_STATUS=WHATIF_COMPLETE`
   - `BACKUP_STATUS=PLANNED`
   - `INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY`
   - `APP_ENTRYPOINT_MUTATION=PLANNED_EXPLICIT_MOUNT_ONLY`
4. Apply creates an install preimage manifest.
5. `Test-CommandCenterV1RevBStatic.ps1` passes.
6. `python -m pytest backend/tests/test_command_center_read_only.py backend/tests/test_api.py -q` passes.
7. Run backend via the project’s standard command, browse `/command-center`, and confirm:
   - Arabic RTL UI loads;
   - one approved task is shown;
   - status shows `APPROVED_FOR_READ_ONLY_RUN`;
   - execution shows `NOT_EXECUTED`;
   - no mutation controls exist.
8. Confirm `POST /api/v1/local-agents/dashboard` returns HTTP 405.

No pilot execution is authorized by this UAT.
