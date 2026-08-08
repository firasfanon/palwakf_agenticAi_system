# Error Record — Product Start Screen Read-Only Apply

## ER-20260706-01 — المرجع الحاكم الكامل غير متاح ضمن الإدخال

- **السبب:** لم يُرفق `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` نفسه؛ المتاح كان snippets فقط.
- **الأثر:** لا يمكن الادعاء بتحديث الدليل الحاكم مباشرة.
- **ما فشل:** لا شيء تقني في الـApply؛ القيد توثيقي.
- **المعالجة:** أُنتج `GUIDE_UPDATE_SNIPPET_PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE_20260706_PRODUCT_READ_ONLY_APPLY.md`.
- **آخر baseline مستقر:** `WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED`.

## ER-20260706-02 — UAT Runtime على Windows غير منفذ

- **السبب:** التفويض الحالي Apply داخل worktree فقط؛ لا يسمح بتشغيل FastAPI أو متصفح أو Network/HAR.
- **الأثر:** لا يرقى الـApply إلى baseline مقبول.
- **المعالجة:** Runbook منفصل موجود داخل الحزمة.

## ER-20260706-03 — PowerShell apply runner لم ينفذ هنا

- **السبب:** بيئة الدليل الحالية لا تحتوي `pwsh` ولا وصولًا إلى مشروع Windows الأصلي.
- **الأثر:** السكربت المرفق راجعته بوصفه artifact ومقيد بفحوص pre/post، لكن التحقق التنفيذي منه على Windows ما زال مطلوبًا ضمن تشغيل المستخدم المحلي.
- **الحل:** استخدم السكربت فقط مع الـworktree الحقيقي وبالتفويض الحالي، ثم احتفظ بـ`APPLY_REPORT.json`.
