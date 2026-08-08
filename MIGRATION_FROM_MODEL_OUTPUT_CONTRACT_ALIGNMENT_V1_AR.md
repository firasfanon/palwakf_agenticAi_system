# Migration from Model Output Contract Alignment Closure V1

This package replaces the following files inside `palwakf_local_agents`:
- `runtime/ReadOnlyRuntimeContextEvidenceV1.psm1`
- `task_contracts/MODEL_OUTPUT_CONTRACT_V1.json`
- `scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1`

It adds:
- `scripts/Test-ExactOutputBoundaryTrailingTextClosureV1.ps1`
- `scripts/Invoke-ExactOutputBoundaryTrailingTextEvalsV1.ps1`
- exact-output governance policy.

No platform files are modified.
