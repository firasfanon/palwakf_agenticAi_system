# معمارية نموذج تشغيل المساعدين المحليين V1

## الحالة

هذا الملف جزء من حزمة Apply مضبوطة، ولا يصبح جزءًا من المصدر إلا بعد تفويض Apply مستقل.

## القرار

```text
CORE_AGENT_OPERATING_MODEL = CORE_AGENT_OPERATING_MODEL_V1
AGENT_OUTPUT_AUTHORITY = PROPOSAL_ONLY_NO_EXECUTION
WORKSPACE_SCOPE = REQUIRED
TASK_BINDING = OPTIONAL_FOR_PREPARE_REQUIRED_BEFORE_OPERATIONAL_ACTIVATION
```

## تعريف المساعد المحلي

المساعد المحلي في هذه المرحلة ليس منفذًا ذاتيًا. دوره هو إنتاج مخرج تحضيري أو مقترح إجراء قابل للمراجعة، مع منع التنفيذ والكتابة والتشغيل.

## دورة الارتباط

```text
Workspace
→ Governed Task / optional task_id during prepare
→ Agent Preparation
→ Review Packet
→ Proposal-only output
→ No execution authority
```

## حدود غير متغيرة

```text
SOURCE_MUTATION = ONLY_AFTER_EXPLICIT_APPLY
DATABASE_WRITE = NONE_BY_PACKAGE_PREPARATION
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
GIT_WRITE = NONE
EXTERNAL_NETWORK = NONE
EVIDENCE_LEDGER = SECONDARY_SUPPORTING_LAYER_ONLY
```
