# Human Approval Gates V2

Explicit human approval is required for:
- any move beyond L1;
- auth, RBAC, RLS, database schema, storage, or migration work;
- external communications;
- staging or production deployment;
- secrets access or rotation;
- legal/privacy content;
- deletion or rollback affecting data;
- memory/skill/prompt promotion after a learning candidate.

## Approval request minimum fields
- requested action,
- risk,
- scope and affected assets,
- alternatives,
- evidence,
- rollback,
- expiry,
- approver decision.
