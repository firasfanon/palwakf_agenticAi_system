# Error Record — npm ci internal registry provenance

## Trigger

Windows local UAT reached `NPM_CI` after successful Python, Edge, Node/npm discovery and isolated worktree copy. `npm ci` exited 1 with `npm error Exit handler never called!`.

## Root cause

The supplied package-lock file includes 113 `resolved` URLs pointing to the assistant build environment private registry. That creates an undeclared external build dependency not accessible from the target Windows environment. The npm CLI error text is treated as an npm-internal failure symptom; the lockfile provenance is the configuration defect corrected here.

## Files

- `frontend/package-lock.json`
- `scripts/Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1`
- `scripts/Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1`

## Remediation

V7 rewrites only resolved endpoint prefixes and uses a per-run registry cache. No package version, integrity checksum, application source, safety flag, model setting, or authorization contract changes.

## Acceptance boundary

Requires V7 Repair PASS, Static Gate PASS, then a fresh Windows UAT run. No baseline change until those runtime results exist.
