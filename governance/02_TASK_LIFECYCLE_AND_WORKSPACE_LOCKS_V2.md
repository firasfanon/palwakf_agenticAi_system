# Task Lifecycle and Workspace Locks V2

## Task states
`Draft -> Ready -> Planned -> AwaitingApproval -> InProgress -> Blocked -> ReviewRequired -> Accepted -> Released -> Reverted -> Archived`

## Entry requirements for Ready
- goal, scope and non-scope are explicit;
- acceptance criteria are testable;
- references are known;
- risk and requested autonomy are assigned;
- dependencies are known;
- reviewer and rollback are assigned for high-risk work.

## Workspace locks
A lock is required for any shared file, folder, API contract, schema, or environment.
No two agents may own the same sensitive resource simultaneously.

## Foundation V2 behavior
No write workspace is created. Locks may be recorded only for planning and future orchestration.
