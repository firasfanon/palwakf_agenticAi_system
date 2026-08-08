# دليل التطبيق — Governed Operations Workbench & Audit Assurance V2

هذه الدفعة توسع Governed Operations فقط. لا تعدل Command Center أو app.py.

## حدود ثابتة
- SQLite محلي فقط.
- لا توجد أي بوابة execute أو dispatch.
- Model Execution = NONE، Pilot = NOT_EXECUTED.
- تطبيق الملفات لا ينشئ أو يغير قاعدة SQLite؛ Migration V2 ينفذ فقط عند أول وصول Runtime لمسار Governed Operations.
- كل كتابة مستقبلية تتطلب فعلًا بشريًا صريحًا داخل مساحة Operations.

## قبول ما قبل التطبيق
يجب تشغيل Syntax ثم Preflight ثم WhatIf. لا يطبق Candidate دون تفويض مستقل.
