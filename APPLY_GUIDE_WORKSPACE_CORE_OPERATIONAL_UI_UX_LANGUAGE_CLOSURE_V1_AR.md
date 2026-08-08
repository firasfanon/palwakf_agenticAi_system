# دليل التطبيق — Workspace Core Operational UI/UX Language Closure V1

هذه الحزمة تعدل واجهة `/workspaces` فقط لمعالجة تجاوز النص وتحسين العرض العربي. يجب تنفيذ Preflight وWhatIf قبل أي Apply.

## ملخص الحماية
- النسخة الاحتياطية تشمل الملفات التي سيتم تعديلها فقط.
- لا تعديل لـ `app.py` أو Core أو API أو Policy Packs.
- لا تهيئة SQLite أثناء Installer.
- لا تشغيل نموذج أو Pilot.

## إعادة التحقق بعد التطبيق
- نفذ Static Gate.
- نفذ `pytest backend/tests/test_workspace_core.py` باستخدام `.venv\Scripts\python.exe`.
- نفذ Browser UAT منفصلًا وفق ملف UAT.
