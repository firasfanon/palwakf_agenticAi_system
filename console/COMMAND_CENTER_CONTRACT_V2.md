# Local Agent Command Center — Contract V2

## Purpose
واجهة محلية مستقبلية لإدارة المهام والوكلاء والأدلة والمراجعات، وليست واجهة محادثة عامة فقط.

## Required views
1. Agent Registry: role, status, skills, autonomy ceiling, admission state.
2. Task Queue: state, risk, owner, dependencies, requested autonomy.
3. Task Run: references, facts, assumptions, evidence, missing proof, next action.
4. Skills: contract, inputs, outputs, eval state, enabled/disabled state.
5. Evidence & Review: accepted/rejected evidence and human decisions.
6. Memory: approved facts, decisions, baselines, error patterns, learning candidates.
7. Locks & Tool Audit: planned/active locks and future tool usage logs.
8. Health: build/lint/test/UAT evidence and open risks.
9. Approvals: high/critical decisions only.

## Explicitly excluded in first UI
- Free unrestricted shell.
- SQL console.
- Deploy / publish buttons.
- Secret viewer.
- Direct production controls.
- Unreviewed memory promotion.

## Local binding
`127.0.0.1` only, pending a separate authentication and owner-session design.
