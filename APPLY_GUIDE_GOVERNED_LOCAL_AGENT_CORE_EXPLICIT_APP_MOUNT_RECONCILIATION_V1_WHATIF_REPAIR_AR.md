# دليل التطبيق — إصلاح WhatIf لحزمة ربط Governed Local Agent Core

## طبيعة الحزمة

هذه **حزمة إصلاح لمسار التحقق فقط** داخل Candidate ربط `local_agent_core` بـ`app.py`. لا تنسخ ملفات الوكلاء ولا تغيّر مشروعك في مرحلة `-WhatIf`.

## التسلسل الإلزامي

1. Candidate Syntax من هذه الحزمة.
2. Preflight من هذه الحزمة.
3. True WhatIf من هذه الحزمة دون `-Apply`.
4. تفويض Apply منفصل لاحقًا.

## أمر WhatIf

```powershell
& $installerScript `
  -ProjectRoot $target `
  -PackageRoot $package `
  -PreflightManifest $preflightManifest `
  -Mode Upgrade `
  -WhatIf
```

## نتيجة القبول

```text
INSTALL_STATUS=WHATIF_COMPLETE
WHATIF_MODE=TRUE
APPLY_SWITCH=NOT_REQUIRED_FOR_WHATIF
PREDICTED_WORKSPACE_CORE_IMPORT_COUNT=1
PREDICTED_WORKSPACE_CORE_MOUNT_COUNT=1
PREDICTED_LOCAL_AGENT_CORE_IMPORT_COUNT=1
PREDICTED_LOCAL_AGENT_CORE_MOUNT_COUNT=1
TARGET_MUTATION_SCOPE=APP_PY_ONLY
PROJECT_MUTATION=NONE
LOCAL_SQLITE_WRITE=NONE
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
```

## ممنوع في هذه المرحلة

- لا تستخدم `-Apply`.
- لا تشغّل Uvicorn أو Runtime UAT.
- لا تُنشئ SQLite أو Task أو Review Packet.
- لا تشغّل Ollama أو أي نموذج.
