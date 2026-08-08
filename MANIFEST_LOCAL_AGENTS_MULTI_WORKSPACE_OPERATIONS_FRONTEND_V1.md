# Manifest — Local Agents Multi-Workspace Operations Frontend V1

## Candidate class
`DESIGN_BASELINE_DISCOVERY_CANDIDATE`

## Status
`BASELINE_BINDING_REQUIRED_BEFORE_UI_APPLY_CARRIER`

## Governing correction
لا يوجد دليل مقبول في الخط الأساس الحالي يثبت React أو Vite أو Tailwind. المسار المعروف لواجهة Multi-Workspace هو:

- `backend/src/palwakf_local_agents/workspace_core/static/index.html`
- `backend/src/palwakf_local_agents/workspace_core/static/styles.css`
- `backend/src/palwakf_local_agents/workspace_core/static/app.js`

لذلك يعتمد التصميم على Vanilla Static Frontend ما لم يكشف الجرد عن طبقة إضافية مثبتة.

## Planned user-facing surfaces
1. Command Center operational overview.
2. Workspace switcher and context shell.
3. Workspace overview, tasks, projects, research, evidence, reviews, tools.
4. Commercial client context and client-boundary visibility.
5. Actor/workspace/client scope status with default-deny explanation.
6. Evidence ledger explorer and human review queue.
7. Pilot control review surface without model execution.
8. Diagnostics, loading, error, empty, and denied states.
9. Arabic-first RTL, responsive narrow viewport, accessibility baseline.

## Non-negotiable controls
- No fake successful data.
- No token storage in browser persistence.
- No actor bypass.
- No cross-workspace selector leakage.
- No client context omission on commercial surfaces.
- No model prompt from the frontend.
- No source write before exact baseline binding.
