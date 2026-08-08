# دليل عربي — إصلاح تقرير Preflight لربط Multi-Workspace Core

## طبيعة الإجراء

هذه الحزمة **تصحيح لحزمة التحقق نفسها**، وليست تطويرًا للمشروع ولا تطبيقًا على `app.py`.

المشكلة التي عالجتها: في Windows PowerShell 5.1 ظهر السطر `WORKSPACE_CORE_SOURCE_EXPECTED_COUNT` كقائمة `1 1 1 ...` بدل العدد المفرد `17`، ولذلك ظهرت علامة `PRECONDITION_WORKSPACE_CORE_SOURCE_HASHES=FAIL` رغم أن `EXACT_MATCH=17` و`PREFLIGHT_RESULT=PASS` كانا صحيحين.

## ما الذي تغير داخل الحزمة؟

- `Test-MultiWorkspaceCoreExplicitAppMountReconciliationV1Preflight.ps1` فقط.
- تم استخراج خصائص `source_files` كـ`NoteProperty` ثم تحويلها إلى مصفوفة صريحة.
- تم حساب `expectedCount` كعدد صحيح واحد.
- تمت إضافة مؤشر `PREFLIGHT_REPORTING_CONSISTENCY`.

## ما الذي لم يتغير؟

- Installer الذي يلمس `app.py` لم يتغير.
- لا توجد كتابة إلى المشروع أثناء syntax أو preflight.
- لا يوجد تشغيل نموذج أو Pilot أو SQLite أو منصة.

## الفحص المسموح الآن

شغّل Syntax ثم Preflight من هذه الحزمة. النتيجة المقبولة يجب أن تتضمن:

```text
WORKSPACE_CORE_SOURCE_EXPECTED_COUNT=17
WORKSPACE_CORE_SOURCE_EXACT_MATCH_COUNT=17
PRECONDITION_WORKSPACE_CORE_SOURCE_HASHES=PASS
PREFLIGHT_REPORTING_CONSISTENCY=PASS
PREFLIGHT_RESULT=PASS
```

بعد ذلك، يبقى تطبيق `app.py` محتاجًا لتفويض Apply منفصل وصريح.
