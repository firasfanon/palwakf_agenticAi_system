# دليل فحص إصلاح Preflight Anchor Reconciliation — عربي

## طبيعة الإجراء

هذه الحزمة لا تطبق Bootstrap ولا تنشئ مساحات عمل. هي تعيد تنفيذ:

1. **Syntax / فحص الصياغة:** التأكد من سلامة الحزمة وأن منطق إصلاح المرساة موجود.
2. **Preflight / فحص ما قبل التطبيق:** قراءة المشروع، وعدّ الاستيراد والتركيب الصحيحين في `app.py`.
3. **WhatIf / محاكاة التطبيق:** عرض إنشاء ثلاث مساحات عمل مستقبلًا دون كتابتها.

## ما الذي لن يحدث

```text
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
SHELL_EXECUTION=NONE
GIT_WRITE=NONE
PROJECT_FILE_WRITE=NONE
DEPLOYMENT=NONE
EXTERNAL_NETWORK=NONE
PROJECT_MUTATION=NONE
```

## معيار القبول

```text
CANDIDATE_PREFLIGHT_ANCHOR_REPAIR_CONTRACT=PASS
LOCAL_AGENT_CORE_IMPORT_COUNT=1
LOCAL_AGENT_CORE_MOUNT_COUNT=1
PREFLIGHT_RESULT=PASS
INSTALL_STATUS=WHATIF_COMPLETE
```

لا يتم استعمال `-Apply` قبل تفويض مستقل بعد اكتمال WhatIf.
