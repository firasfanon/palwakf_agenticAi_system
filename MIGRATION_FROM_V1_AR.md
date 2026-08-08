# Migration from Foundation V1 to Agentic Operating System V2

## طبيعة الترقية
هذه ترقية تنظيمية وحوكمية. لا تنقل بيانات تشغيلية ولا تعدل منصة PalWakf ولا تشغّل الوكلاء.

## ما يُحفظ
لا يحذف Script التثبيت:
- `tasks/`
- `evidence/`
- `output/`
- `audit/`
- `reference_sources/`
- تقارير Wave A أو الملفات المرجعية السابقة.

## ما يُضاف أو يُحدّث
- `agents/registry_v2.yaml`
- `agents/<role>/AGENT_CHARTER_V2.md`
- `agents/<role>/SYSTEM_PROMPT_V2_AR.md`
- `skills/`
- `governance/*_V2.md`
- `task_contracts/*_v2.json`
- `memory/`
- `evals/`
- `scripts/Install-AgenticOperatingSystemV2.ps1`
- `scripts/Test-AgenticOperatingSystemV2.ps1`

## تصحيح مهم
الملفات القديمة `SYSTEM_PROMPT_AR.md` لا تُحذف ولا تُستخدم تلقائيًا بعد الترقية.
يصبح اختيار Prompt V2 قرارًا صريحًا في runner مستقبلي بعد اجتياز اختبارات القبول.

## لا تغيّر هذه الحزمة
- لا تمنح أي دور حق تعديل منصة أو Git.
- لا تحوّل التقارير أو المحادثات إلى ذاكرة معتمدة تلقائيًا.
- لا تسمح بتشغيل Production أو Staging.
- لا تطلب أو تنقل أسرارًا.
