# PROJECT STATE MANAGER V1 — DESIGN ONLY

## الغرض

هذه الدفعة تعرف طبقة `Project State Manager` كموديل حالة موحد يجمع:

- Goal State
- Plan Draft State
- Tool Selection State
- Task Drafts State
- Review Status State
- Charter Boundary State
- Runtime/Execution State

## الحقيقة التشغيلية

هذه ليست طبقة تخزين دائم وليست Execution Engine. إنها طبقة تصميم وواجهة تساعد على رؤية الحالة وتحديد شروط الاستئناف لاحقًا.

## نموذج الحالة المقترح

```json
{
  "goal_state": "declared/prepared",
  "plan_draft_state": "prepared/review_pending",
  "tool_selection_state": "contract_mapped_only",
  "task_drafts_state": "draft/ready_for_review/returned/accepted_as_plan",
  "review_state": "human_authority_required",
  "charter_boundary_state": "no_self_apply_no_hidden_execution",
  "execution_state": "blocked_future_gated",
  "persistence": "none"
}
```

## الانتقالات

المسموح الآن:

1. Goal → Plan Draft كتصميم مرئي فقط.
2. Plan Draft → Tool Selection كاختيار مقترح فقط.
3. Tool Selection → Task Draft عبر Backend prepare فقط.
4. Task Draft → Accepted as Plan كمراجعة بشرية فقط.

المحجوب:

- Accepted as Plan → Apply/Execution
- Any State → Self-Apply
- Any State → Hidden Shell/Git/Code/Model/Pilot

## شروط الانتقال المستقبلي إلى تخزين دائم

قبل Local Task Store أو SQLite persistence يجب وجود:

- Schema contract
- State transition audit log
- Rollback/snapshot policy
- Human approval surface
- Failure recovery report

## حدود هذه الدفعة

- لا Model execution.
- لا Pilot execution.
- لا Shell.
- لا Git.
- لا Code execution.
- لا self-apply.
- لا autonomous build.
- لا DB أو SQLite persistence.
- لا Backend mutation.
