# مرشّح ترحيل عقد اختبارات Legacy وPositive Authorization UAT الخادمي V1

**الحالة:** مرشّح تنفيذي للمراجعة فقط؛ غير مطبّق على مشروع Windows وغير مقبول كـBaseline.

## الهدف

ترحيل اختبارات Legacy التي افترضت مسارات غير محددة بمساحة عمل أو كتابة بلا `Authorization` إلى عقد التفويض الخادمي المعتمد، ثم إضافة اختبار إيجابي مضبوط يثبت أن الكتابة المصرّح بها تتم داخل مشروع اختبار مؤقت فقط وبلا تشغيل نموذج أو Pilot.

## لا يشمل

- لا تعديل في `backend/src` أو React أو FastAPI runtime.
- لا إنشاء Actor حقيقي أو تعديل `config/local_actor_scope_registry_v1.json` في المشروع الفعلي.
- لا React write، ولا Pilot، ولا Model execution، ولا Commercial positive UAT، ولا نشر.

## نتيجة التحقق داخل النسخة المعزولة

```text
BASELINE_FULL_BACKEND_SUITE = 48 passed / 16 failed
CANDIDATE_FULL_BACKEND_SUITE = 65 passed / 0 failed
TARGETED_NEGATIVE_UAT = 25 passed
CONTROLLED_POSITIVE_AUTHORIZATION_UAT = 1 passed
PRODUCTION_SOURCE_FILES_CHANGED = 0
```

راجع `DISCOVERY_AND_DESIGN_REPORT_AR.md` و`RUN_GUIDE_AR.md` قبل أي Apply.
