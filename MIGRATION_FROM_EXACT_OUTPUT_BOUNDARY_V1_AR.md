# Migration from Exact Output Boundary and Trailing Text Closure V1

This package is a corrective merge. It replaces the current runtime module, evidence gateway, constrained runner, exact-output test/eval scripts, and baseline read-only eval script.

It restores the missing Evidence Gateway dependency while retaining:
- `OUTPUT_CONTRACT_START`
- 11 ordered contract fields
- `OUTPUT_CONTRACT_END`
- strict rejection of trailing non-contract text
- `TASK_ID` exclusion from model output

No PalWakf platform files are involved.
