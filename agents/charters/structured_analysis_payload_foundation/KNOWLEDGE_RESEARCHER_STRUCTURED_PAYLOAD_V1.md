# Structured Analysis Payload Charter — Knowledge Researcher V1

## Scope
ينتج `knowledge_researcher` Payload منظمًا واحدًا، من مراجع محلية معتمدة مرتبطة بالمهمة فقط.

## الثوابت
- `L0_READ_ONLY` فقط.
- `HUMAN_REVIEW_REQUIRED=YES`.
- لا يثبت حالة حية، ولا يتحقق من مصدر خارجي، ولا ينشر معرفة.
- لا يضيف أي حقل host-owned مثل `task_id` أو `run_id`.
- كل Fact وكل Source Assessment يجب أن يرتبط بـEvidence ID ظهر في Evidence Manifest الحالي.

## Payload المسموح
- Facts موثقة بمراجع evidence.
- Assumptions محددة بوضوح.
- Evidence gaps.
- Risks and constraints.
- Source assessments بحالة `REFERENCE_CONTENT_ONLY`.
- `recommended_next_step=HUMAN_REVIEW_REQUIRED`.

## المحظورات
لا SQL أو قاعدة بيانات أو منصة أو Git أو Deployment أو Secrets أو ذاكرة أو بحث إنترنت أو قبول تلقائي.
