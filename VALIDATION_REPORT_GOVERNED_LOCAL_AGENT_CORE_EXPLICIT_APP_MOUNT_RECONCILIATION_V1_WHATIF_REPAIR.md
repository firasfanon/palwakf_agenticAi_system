# Validation Report — WhatIf Repair Candidate Assembly

## Repair rationale

The prior reconciliation installer contained a valid `$WhatIfPreference` branch but required `-Apply` before reaching it, so a true no-write preview was impossible.

## Repair assertions

- The installer now allows `-WhatIf` without `-Apply`.
- Actual writes still require `-Apply`.
- WhatIf performs the same preflight manifest, source-hash, and anchor checks as Apply.
- WhatIf computes a predicted `app.py` postimage hash and expected 1/1/1/1 anchor counts in memory.
- No backend project postimage file is included or changed by this repair package.

## Static assembly validation

- Package inventory SHA-256 rebuilt after script/doc updates.
- Installer contains the true WhatIf guard.
- Installer emits predicted postimage hash and anchor counts.
- No `Copy-Item` or source-copy path is introduced.

## Required Windows validation

PowerShell Candidate Syntax, Preflight, and true `-WhatIf` must be executed locally before any Apply authorization.
