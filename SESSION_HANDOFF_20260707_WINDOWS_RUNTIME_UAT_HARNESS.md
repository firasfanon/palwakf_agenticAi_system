# Session Handoff — Local Agents Windows Runtime UAT Harness (2026-07-07)

## نقطة الاستئناف الدقيقة

تم تفويض:

```text
AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY
```

لم يُنفذ UAT على Windows داخل هذه الجلسة، لعدم وجود وصول إلى مسار المشروع المحلي أو بيئة Edge/FastAPI على جهاز المستخدم. أُنشئت حزمة Harness قابلة للتشغيل محليًا فقط.

## كشف حاكم مهم

في حزمة الـApply السابقة، سكربت Apply يطبق payload ثم يستدعي Gate يتحقق من Preimage؛ وهذا غير متسق للملفات المعدلة. لا تعتمد نتيجة `STATIC_GATE_PASS` السابقة كدليل قابل لإعادة التنفيذ حتى يتم إصلاح Harness أو إعادة تطبيقه بتسلسل صحيح.

## الحزمة الحالية

- `Invoke-ProductConsoleReadOnlyWindowsRuntimeUatV1.ps1`: Runner Windows.
- `run_read_only_browser_uat.mjs`: Edge CDP browser evidence collector.
- `WINDOWS_EXECUTION_RUNBOOK_AR.md`: أوامر التنفيذ والقبول.
- `HARNESS_RECONCILIATION_ERROR_RECORD_AR.md`: سجل الخطأ والعلاج.

## حدود لا تزال ثابتة

```text
NO_SOURCE_PROJECT_MUTATION
NO_SQLITE_MIGRATION
NO_CLIENT_DATA_WRITE
NO_REACT_WRITE
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_PRODUCTION
```

## منطق القرار بعد التشغيل

1. إذا كانت النتيجة `WINDOWS_RUNTIME_UAT_PASS`: مراجعة الأدلة البشرية أولًا، ثم تفويض منفصل لمصالحة/إصلاح Apply Harness قبل baseline acceptance.
2. إذا كانت `WINDOWS_RUNTIME_UAT_FAIL`: لا baseline؛ تستخدم لقطات/Network/Console لتحديد إصلاح محلي واحد داخل React أو Harness وفق سبب الفشل.
3. إذا كانت `WINDOWS_RUNTIME_UAT_HARNESS_ERROR`: لا تخمّن backend command؛ استخدم `BACKEND_STDERR.log` و`BROWSER_UAT_REPORT.json` لتصنيف سبب بيئي أو تقني.
