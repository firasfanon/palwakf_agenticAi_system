# Baseline — Legacy Test Contract Migration + Controlled Positive Authorization UAT V1

## الحالة

```text
BASELINE_CLASSIFICATION=ISOLATED_REPLICA_ACCEPTED__WINDOWS_PYTHON_3_12_10_CONFIRMATION_PENDING
APPLY_IN_ISOLATED_REPLICA=PASS
PREIMAGE_POSTIMAGE=PASS
TARGETED_NEGATIVE_AND_POSITIVE_UAT=26/26 PASS
FULL_BACKEND_SUITE=65/65 PASS
PRODUCTION_SOURCE_FILES_CHANGED=0
```

## ما تغير

اقتصر التغيير على ثمانية ملفات اختبار/حامل UAT: أربعة اختبارات Legacy جرى ترحيلها لعقود Bearer/Workspace/Actor الحالية، ملف Fixtures مؤقت، اختبار Positive Authorization مضبوط، وسكربتا Static Gate وRunner. لم يتغير `backend/src` إطلاقًا عند المقارنة مع baseline السابق.

## حدود الاعتماد

نفذت الاختبارات في نسخة معزولة داخل بيئة الجلسة باستخدام Python 3.13.5، بينما `pyproject.toml` يعلن `>=3.11,<3.13`. لذلك يلزم تشغيل الحزمة نفسها محليًا على Python 3.12.10 قبل توصيف baseline كـWindows-local accepted.

## قيود دائمة

```text
NO_REACT_WRITE_CONTROL
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_DATABASE_ACCESS_OUTSIDE_DISPOSABLE_TEST_FIXTURES
NO_COMMERCIAL_POSITIVE_UAT
NO_PRODUCTION_PROMOTION
```
