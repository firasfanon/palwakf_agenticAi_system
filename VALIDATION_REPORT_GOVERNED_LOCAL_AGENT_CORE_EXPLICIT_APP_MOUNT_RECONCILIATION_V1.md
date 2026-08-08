# Validation Report — Candidate Assembly

## Design inputs

The user-supplied Preflight diagnostic established:

- 11 `local_agent_core` source/test files equal the approved postimage.
- Workspace Core import/mount count is `1/1`.
- Local Agent Core import/mount count is `0/0`.

## Package assertions

- The Candidate has no project source postimage to copy.
- Candidate Syntax parses all package PowerShell scripts via PowerShell runtime on Windows.
- Preflight must verify the exact 11 source hashes before emitting a manifest.
- WhatIf must make no project mutation.
- Actual Apply changes only `app.py`, backs it up, and parses Python after writing.

## Required Windows validation

PowerShell Candidate Syntax, Preflight and WhatIf have not been executed in this build environment and remain mandatory before any Apply.
