# Evidence Gateway Dependency Restoration Policy V1

## Purpose
Restore the evidence-manifest dependency that was removed when the exact-output boundary runtime module replaced the prior shared runtime module.

## Required merged runtime contract
The runtime module must export both groups:

1. Evidence gateway functions:
   - `Get-ReadOnlyEvidenceRoot`
   - `ConvertTo-SafeRelativeReferencePath`
   - `Get-ReferenceSecurityFlags`
   - `New-ReferenceEvidenceManifest`

2. Exact model-output functions:
   - `Get-ReadOnlyModelOutputContractV1`
   - `Get-Sha256TextV1`
   - `Test-ReadOnlyModelOutputV1`

## Safety invariants
- Reference paths are restricted to `reference_sources/approved`.
- Approved reference content is untrusted and non-executable.
- A direct manifest probe reads only the pilot reference and creates no output file.
- No platform mutation, database access, Git write, deployment, or secrets access is authorized.
- Model execution remains disabled until static tests and deterministic evaluations pass.

## Required verification sequence
1. Upgrade WhatIf.
2. Actual upgrade.
3. `Test-EvidenceGatewayDependencyRestorationMergeClosureV1.ps1`.
4. Exact-output static test.
5. Exact-output deterministic evaluations.
6. Baseline read-only deterministic evaluations.
7. Gateway-only run, without `-Execute`.
8. Human review before one pilot model execution.
