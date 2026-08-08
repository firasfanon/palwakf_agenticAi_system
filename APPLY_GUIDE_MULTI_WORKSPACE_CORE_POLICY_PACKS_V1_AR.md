# دليل تطبيق Multi-Workspace Core + Policy Packs V1

## قبل التطبيق
- تحقق من Hash للحزمة.
- نفّذ Syntax Gate وPreflight وWhatIf.
- لا تطبق إذا كان `app.py` لا يحتوي على `mount_governed_operations(app, project_root=PROJECT_ROOT)`؛ ذلك يدل على Baseline مختلف.

## نطاق التطبيق
- ملفات جديدة فقط باستثناء `app.py` الذي يتلقى import/mount واضحين.
- لا تحدث أي كتابة SQLite أثناء التثبيت.

## بعد التطبيق
- شغّل الاختبارات.
- نفّذ Runtime Probe لمسارات `/api/v1/workspaces/*`.
- Browser UAT لمسار `/workspaces` فقط.
