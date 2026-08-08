# Structured Analysis Payload Charter — Documentation Handoff V1

## Scope
ينتج `documentation_handoff` مسودة Handoff منظمة ومقتبسة من أدلة مرتبطة بالمهمة فقط.

## الثوابت
- `L0_READ_ONLY` فقط.
- `HUMAN_REVIEW_REQUIRED=YES`.
- لا يعدل أي ملف توثيق، ولا يكتب Baseline حقيقيًا، ولا يرقّي ذاكرة.
- كل Fact وكل Handoff Section يحمل Evidence ID من Evidence Manifest الحالي.
- الـHost وحده ينشئ envelope وحقول `task_id` و`run_id`.

## Payload المسموح
- Facts موثقة.
- Assumptions, evidence gaps, risks/constraints.
- Handoff sections من: `CURRENT_STATE`, `EVIDENCE`, `OPEN_ITEMS`, `RESUMPTION_POINT`.
- `recommended_next_step=HUMAN_REVIEW_REQUIRED`.

## المحظورات
لا تعديل منصة أو قاعدة بيانات أو Git أو نشر أو أسرار أو وصول شبكي أو قبول إغلاق تلقائي.
