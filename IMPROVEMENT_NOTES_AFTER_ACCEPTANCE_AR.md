# ملاحظات التحسين بعد قبول Mega Batch 01–06

هذه الملاحظات تنفذ **بعد** قبول الحزمة الموحدة، ولا تدخل ضمن تغيير وظائف الإنتاج.

1. كل حزمة PowerShell جديدة تمر عبر `Windows PowerShell 5.1 parse test`.
2. كل سكربت يحتوي نصوصًا غير ASCII يحفظ UTF-8 with BOM؛ ويفضل أن يبقى Runtime script ASCII-only.
3. كل حزمة تحمل Runtime Self-Test قبل لمس المشروع.
4. كل حزمة Apply تحتوي WhatIf قابلًا للتكرار ومثبتًا بالمخرجات.
5. يثبت `PACKAGE_INVENTORY.json` وSHA-256 قبل التشغيل.
6. نقل أدلة القبول من `%TEMP%` إلى Evidence Ledger دائم قبل أي حذف دوري للملفات المؤقتة.
7. تقرير ختامي موحد: baseline, changes, tests, UAT, non-goals, backup, rollback, residual debt.


> **ملاحظة إصلاح G0–G2:** مرشح الإصلاح الحالي يضيف ربط Manifest بالحزمة وفحصًا تشغيليًا ذاتيًا لـPreflight وWhatIf قبل أي Apply لاحق.
