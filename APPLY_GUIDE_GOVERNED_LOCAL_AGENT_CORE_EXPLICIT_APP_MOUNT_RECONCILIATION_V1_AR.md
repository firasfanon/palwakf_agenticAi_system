# دليل التطبيق — ربط Governed Local Agent Core صراحةً بـ app.py

## طبيعة الحزمة

هذه حزمة **Reconciliation** وليست إعادة تطوير للمكوّن. تثبت أولاً أن 11 ملفاً من `local_agent_core` موجودة وتطابق Postimage المعتمد، ثم تضيف import وmount واحدين فقط إلى `app.py`.

## التسلسل الإلزامي

1. Candidate Syntax.
2. Preflight فقط.
3. WhatIf فقط.
4. تفويض Apply منفصل.
5. Post-Apply Technical Verification.
6. Runtime Read-Only UAT منفصل.

## القيود

- لا ينسخ Installer أي ملف من `local_agent_core/**`.
- لا يغيّر `workspace_core` أو `governed_operations` أو `command_center` أو `policy_packs`.
- لا ينشئ SQLite أثناء التثبيت.
- لا يشغّل نموذجاً أو Pilot.
