# UAT — Workspace Core Operational UI/UX Language Closure V1

## قبل التطبيق
- تحقق من Hash حزمة Candidate.
- نفذ Syntax Gate وPreflight وWhatIf.
- يجب أن تكون ملفات UI الحالية مطابقة لـpreimage المقيد داخل Candidate.

## بعد التطبيق
1. شغّل FastAPI بواسطة `.venv\Scripts\python.exe`.
2. افتح `/workspaces` في عرض سطح مكتب ثم عرض ضيق لا يقل عن 360px.
3. تحقق من:
   - ظهور أربع مساحات عمل.
   - عدم وجود تجاوز نصي أو تداخل بين البطاقات.
   - عرض التسميات العربية التشغيلية بدل قيم Enum الخام.
   - وجود قسم "تفاصيل تقنية خام" مطوي فقط بعد اختيار مساحة.
   - عدم وجود أزرار إنشاء أو تنفيذ أو تشغيل نموذج.
4. اختبر اختيار كل بطاقة مرة واحدة وتأكد أن تفاصيلها تعرض دون خطأ.

## نتائج القبول
```text
WORKSPACE_UI_CARD_OVERFLOW=NONE
WORKSPACE_UI_CROSS_CARD_COLLISION=NONE
WORKSPACE_UI_RTL=PASS
WORKSPACE_UI_ARABIC_OPERATIONAL_LABELS=PASS
WORKSPACE_UI_RAW_VALUES_COLLAPSED=PASS
WORKSPACE_UI_RESPONSIVE_NARROW=PASS
WORKSPACE_API_WRITE_OPERATIONS=NONE
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
```
