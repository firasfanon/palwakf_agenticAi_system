# Human Approval Gate V1

A human reviewer must explicitly approve or reject a Task, Memory record, or Learning candidate. Approval is logged in `audit/events.jsonl` and a decision record is written beside the approved or rejected artifact.

No agent may approve its own task, memory, policy, skill, or capability expansion.

V1 approvals do not authorize SQL, Git write, deployment, secrets, production, or platform mutation.
