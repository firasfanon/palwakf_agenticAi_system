# Memory, Evidence and Controlled Learning Policy V2

## Memory categories
- Working: task-local, expires after completion.
- Project: current state, baselines, backlog.
- Semantic: verified facts and system contracts.
- Episodic: accepted runs, incidents and batches.
- Procedural: accepted skills and SOPs.
- Error: root causes and regression rules.
- Feedback: human acceptance/rejection patterns.
- Sensitive: restricted metadata; never automatically surfaced.

## Admission rule
`Observation -> Learning Candidate -> Evidence + Tests -> Independent/Human Review -> Approved or Rejected`
No raw chat, model output, user file, or failed hypothesis becomes approved memory automatically.

## Evidence rule
A statement by an agent is not evidence.
Accepted evidence includes controlled test output, build/lint results, reviewed diff, redacted logs, UAT evidence, and verified static trace.
