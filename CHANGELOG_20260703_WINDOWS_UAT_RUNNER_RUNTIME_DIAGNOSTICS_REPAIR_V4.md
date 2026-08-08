# Changelog — Windows UAT Runner Runtime Diagnostics Repair V4

- Replaced null-unsafe external output `.Trim()` calls in the UAT runner.
- Added stage-aware runtime diagnostics and `FAILED.txt` evidence output.
- Added a narrow replacement utility with parser and hash verification plus rollback backup.
- Scope: runner tooling only; no changes to React, FastAPI, safety flags, lockfile, or application data.
