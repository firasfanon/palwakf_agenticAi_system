# Apply Guide

1. Run Candidate syntax gate.
2. Run target Preflight.
3. Run installer with `-WhatIf`.
4. Inspect scope: explicit app mount + new module + test/docs only.
5. Apply only with an explicit APPLY authorization.
6. Run tests and browser UAT.

The installer creates exact preimages before copying any file. The first governed-operations API request (or test) will initialize the separate SQLite file:
`audit/governed_operations.sqlite`.
