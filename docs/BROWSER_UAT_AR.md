# Browser UAT — Frontend V1

بعد نجاح `Install` و`PostApply`، شغّل الخادم المحلي وفق آليتك المعتادة فقط (ليس جزءاً من هذه الحزمة) ثم راجع:

1. `/command-center`
   - التنقل بين Dashboard / Tasks / Reviews / Evidence / Agents / Governance / Health.
   - في شاشة ضيقة: زر القائمة يعمل وEscape يغلقها.
   - لا يوجد زر تشغيل أو نموذج كتابة.

2. `/workspaces`
   - تظهر أربع مساحات عمل.
   - اختيار مساحة يعرض Policy/Readiness/Integrity.
   - روابط Operations وLocal Agents تحمل `workspace_id` الصحيح.

3. `/operations?workspace_id=research_learning`
   - يظهر ملخص/Tasks/Reviews/Evidence/Assurance/Controls.
   - لا تظهر أي form أو زر submit أو create evidence.
   - تبديل المساحة لا يعرض معلومات مساحة مختلفة داخل الـURL والسياق.

4. `/local-agents?workspace_id=personal_development`
   - قائمة المساحات تعمل.
   - رابط Operations يتغير مع المساحة.
   - لا يوجد إدخال Token أو زر تشغيل نموذج أو Pilot.

5. افتح DevTools > Network:
   - تحقق أن هذه الواجهات لا ترسل طلبات POST.
   - لا يوجد `Authorization` header صادر من scripts.
