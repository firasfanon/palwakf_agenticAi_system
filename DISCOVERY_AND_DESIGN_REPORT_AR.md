# تقرير Discovery/Design — Legacy Test Contract Migration + Controlled Positive Authorization UAT V1

## المدخل المعتمد

اعتمدت النسخة المعزولة المستخرجة من:

```text
PALWAKF_LOCAL_AGENTS_LEGACY_WRITE_AUTHORIZATION_CLOSURE_AND_NEGATIVE_UAT_V1_APPLIED_SOURCE_20260704.zip
```

لم يتوفر `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` ضمن المصدر؛ لذلك يتضمن المرشّح `GUIDE_UPDATE_SNIPPET...` فقط ولا يدّعي تعديل المرجع الأعلى.

## سبب الفشل السابق

فشل Backend suite السابق بـ`48 passed / 16 failed` لأن اختبارات Legacy كانت تفترض واحدًا أو أكثر من الآتي:

1. مسارات `governed-operations` غير المحددة بـ`workspace_id`.
2. طلبات كتابة دون Bearer Actor، بعد أن أصبح Actor authentication إلزاميًا.
3. Actors تجريبية بلا registry مهيأ ضمن `tmp_path`.
4. توقعات Health/UI markers لم تعد جزءًا من العقد التشغيلي الحالي.
5. محاولة كتابة Capability Foundation قبل تهيئة مساحة Foundation المسموح بها.

هذه ليست مبررات لإزالة التفويض؛ بل هي ديون اختبار يجب ترحيلها إلى العقد الخادمي الجديد.

## تصميم المرشّح

- إضافة `backend/tests/conftest.py` كمُهيئ اختبار فقط، ينسخ policy packs/workspaces إلى `tmp_path` ويكتب registry تجريبي `default_access=DENY` مع tokens hashed محلية.
- ترحيل اختبارات `governed_operations` و`local_agent_core` إلى مسارات Workspace وعناوين `Authorization` حقيقية ضمن fixture.
- تحديث تحقق واجهة Workspace Core ليتحقق من رموز موجودة فعلًا بدل marker تاريخي غير موجود.
- إضافة `test_legacy_write_authorization_positive_uat.py`:
  - Government: Governed Operations lifecycle + Local Agent preparation.
  - Research only: Capability Foundation task، لأن `palwakf_government` غير مفعّل لتخزين Foundation.
  - Commercial: مستبعد صراحة.
  - Pilot: لا يُستدعى.
  - كل state في `tmp_path` وتثبت قائمة postimage المسموحة فقط.

## نتيجة التحقق المرشّح

```text
PYTHON_COMPILE = PASS
FULL_BACKEND_SUITE = 65 passed / 0 failed
WARNINGS = 54 FastAPI on_event deprecation warnings
PRODUCTION_SOURCE_TREE_HASH_EQUALITY = PASS
```

تحذيرات FastAPI ليست ضمن نطاق هذا المرشّح ولا تُصنف نجاحًا أو فشلًا وظيفيًا.
