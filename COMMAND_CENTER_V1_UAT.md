# Command Center V1 — UAT

## Expected current state
- `SAPF_DOCUMENTATION_HANDOFF_PILOT_001` appears as `APPROVED_FOR_READ_ONLY_RUN`.
- The dashboard labels it as not executed.
- No buttons exist to execute, approve, archive, or mutate state.

## Browser UAT
1. Open `/command-center` on desktop and mobile widths.
2. Open each of: tasks, task detail, reviews, evidence, agents, governance, system health.
3. Confirm Arabic RTL layout and no console errors.
4. Confirm Task Detail displays the explicit separate-authorization notice.
5. Confirm every screen is readable without allowing mutation.

## API UAT
1. `GET /api/v1/local-agents/dashboard` returns 200.
2. `GET /api/v1/local-agents/tasks` returns task queue metadata.
3. `GET /api/v1/local-agents/tasks/SAPF_DOCUMENTATION_HANDOFF_PILOT_001` returns 200.
4. `GET /api/v1/local-agents/tasks/../.env` is rejected.
5. `POST /api/v1/local-agents/dashboard` returns 405.

## Required regression
Run existing Lifecycle Closure, SAPF and Pack01 static/eval scripts unchanged after integration.
