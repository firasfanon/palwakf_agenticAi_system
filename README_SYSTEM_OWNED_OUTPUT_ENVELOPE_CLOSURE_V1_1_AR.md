# PALWAKF Local Agents — System-Owned Output Envelope Closure V1.1

## نبذة بالعربية
هذه نسخة توافقية مكتملة. فحص V1 أثبت أن الحزمة لم تشمل تحديث ملفي الـBaseline Evals وReport Rendering Test، لذلك لم تكن قابلة للتثبيت بأمان رغم أن مكوناتها الأساسية صحيحة.

## ما تعالجه V1.1
- Contract V3: النموذج يعيد 11 سطر key/value فقط.
- المضيف المحلي ينشئ `OUTPUT_CONTRACT_START` و`OUTPUT_CONTRACT_END` بعد تحقق الجسم.
- Raw output وCanonical output محفوظان بشكل منفصل.
- Run mode تحت `-Execute` يبقى `READ_ONLY_CONTEXT_EVIDENCE_MODEL_RUN`.
- أي نص سابق أو لاحق أو `TASK_ID` أو علامات حدود يقدّمها النموذج يبقى مرفوضًا.
- Evidence Gateway وإصلاح Security signals وMarkdown fences محفوظة.
- Baseline Evals أصبح متوافقًا صراحة مع Contract V3.
- Report Rendering Test أصبح واعيًا بقسم Raw وقسم Canonical.
- أضيف Compatibility Completion Test مستقل.

```text
MODEL_EXECUTION=DISABLED_BY_DEFAULT
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
```

## التحقق المطلوب
1. WhatIf.
2. تثبيت فعلي.
3. Static Test.
4. Compatibility Completion Test.
5. Envelope Evals.
6. Baseline Evals.
7. Report Rendering Test.
8. Dry Run واحد دون `-Execute`.
9. مراجعة التقرير.
10. تشغيل Ollama واحد فقط بعد قبول جميع المراحل.
