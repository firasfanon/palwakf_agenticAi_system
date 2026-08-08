# Changelog — Local Agent Read-only Pilot Lifecycle Closure V1.2 Rev C Candidate

## Rev C corrective changes
- Fixed deterministic-eval hang in Rev B.
- Root cause: recursive descendant copy from `$tempRoot` into `$tempRoot\bad`.
- Negative fixtures now copy to an independent sibling temporary root only.
- Added explicit `EVAL_BAD_ROOT_INSIDE_TEMP_ROOT_FORBIDDEN` containment guard.
- Added `EVAL_STAGE` progress markers for setup, valid review, valid archive, active-state check, negative fixture copy, and rejection cases.
- Added cleanup for both temporary roots.
- Extended static validation to require the recursive-copy guard.

## Scope unchanged
- No Core Runtime / 11-line contract / Registry mutation.
- No Ollama execution, task generation, platform, database, Git, deployment, secrets, or memory write.
