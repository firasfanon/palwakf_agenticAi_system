# دليل تطبيق — إصلاح حزمة التحقق لمسار App Mount Reconciliation V1

## طبيعة الحزمة

هذه الحزمة تصلح **تحقق Candidate داخل الحزمة فقط**. لا تعدل مشروع Local Agents ولا `app.py` عند تنفيذ Syntax أو Preflight أو WhatIf.

## سبب الإصلاح

حزمة WhatIf السابقة نجحت في Preflight وWhatIf لكنها فشلت في Candidate Syntax لأن Script التحقق يطلب أسماء ملفات Manifest/Guide/Validation قديمة لا توجد في الحزمة نفسها.

## التسلسل الإلزامي

1. تحقق SHA-256 للحزمة.
2. فك الضغط إلى مجلد منفصل.
3. شغّل Candidate Syntax.
4. شغّل Preflight.
5. استخرج `PREFLIGHT_MANIFEST` من المخرجات.
6. شغّل Installer بـ`-WhatIf` فقط.
7. لا تستخدم `-Apply` من هذه الحزمة دون تفويض مستقل لاحق.

## النتيجة المقبولة

```text
CANDIDATE_PACKAGE_INVENTORY=PASS
CANDIDATE_POWERSHELL_PARSE=PASS
VALIDATION_DOCUMENT_CONTRACT=PASS
CANDIDATE_SYNTAX_RESULT=PASS
PREFLIGHT_RESULT=PASS
INSTALL_STATUS=WHATIF_COMPLETE
WHATIF_MODE=TRUE
PROJECT_MUTATION=NONE
LOCAL_SQLITE_WRITE=NONE
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
```

## حدود الأمان

- المشروع لا يُكتب في Candidate Syntax أو Preflight أو WhatIf.
- لا يتم نسخ ملفات `local_agent_core`.
- لا يتم تشغيل نموذج أو Pilot.
- لا يتم إنشاء أو كتابة SQLite.
