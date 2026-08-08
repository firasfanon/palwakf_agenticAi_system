# Apply Guide — Command Center V1.1 Rev B

## Before apply
- Run `Test-CommandCenterV1RevBPackageSyntax.ps1`.
- Run `Test-CommandCenterV1RevBPreflight.ps1`.
- Run the installer with `-WhatIf`.
- Do not manually paste Python code into PowerShell.

## Apply
Use only the installer. It patches the real FastAPI entrypoint internally and backs up the exact preimage.

## After apply
- Run the Rev B static check.
- Run the backend tests.
- Start the backend using the project’s existing command and browse `/command-center`.
- Do not run the approved SAPF pilot.

## Safety
`MODEL_EXECUTION=NONE`
`PILOT_EXECUTION=NOT_EXECUTED`
`PLATFORM_MUTATION=NONE`
`DATABASE_ACCESS=NONE`
`GIT_WRITE=NONE`
`DEPLOYMENT=NONE`
`SECRETS_ACCESS=NONE`
`MEMORY_WRITE=NONE`
