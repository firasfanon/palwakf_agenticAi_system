# Read-Only Pilot Human Review and Archive Policy V1

## Scope
This policy applies only to a task already in `tasks/approved` with status `APPROVED_FOR_READ_ONLY_RUN`, which has a completed read-only run and remains subject to human review.

## Required review evidence
- Exact Task ID.
- Exact Run ID.
- Canonical output, raw output, report, and evidence manifest.
- `MODEL_OUTPUT_VALID=True`.
- 11 raw lines, 0 trailing lines, host-owned envelope.
- Report run status `PENDING_HUMAN_REVIEW`.
- Evidence manifest task match and no platform/database/Git/deployment access.

## Decision semantics
`ACCEPTED` means: the reviewer accepts the bounded run as evidence that the constrained pilot lifecycle executed as designed. It does **not** accept a live-state claim, a policy decision, a memory item, a learning candidate, or an operational action.

`REJECTED` means: the pilot run is not accepted for the stated review purpose. The task may still be archived after the decision to prevent repeated execution; the decision reason is retained.

## Archive transition
Only `Archive-ReadOnlyPilotAfterHumanReviewV1.ps1` may move a task from `tasks/approved` to `tasks/archived`. Manual task JSON edits, manual file moves, and deletion of output artifacts are forbidden.

## Preservation
Raw, canonical, report, context, and evidence manifest artifacts remain immutable records. The archive operation stores task metadata and a backup only.

## Prohibitions
No model invocation, platform mutation, database access, Git write, deployment, secrets access, memory write, automatic task approval, or automatic pilot generation.
