# ملف توريث شامل — Product Start Screen & Operational Console Candidate

## نقطة الاستئناف

تم تفويض الدفعة:

```text
AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_UX_UI_DISCOVERY_DESIGN_AND_GOVERNED_READ_ONLY_CANDIDATE_V1
```

واكتملت **كمرشح Discovery/Design/Read-Only فقط**. لا يوجد Apply ولا Runtime UAT ولا baseline acceptance.

## المرجع الأعلى

يجب قراءة `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` إن كان متاحًا في جلسة التنفيذ. لم يكن الملف نفسه ضمن الحزم المتاحة لهذه الدفعة؛ لذلك يوجد Guide Update Snippet فقط.

## baseline الأب

```text
WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED
```

والحالة الفنية السابقة ذات الصلة:

```text
React + TypeScript + Vite = BUILT
FastAPI conditional mount /agent-console = ENABLED
Read-only browser/HTTP UAT = accepted historically
React write = blocked
Model/Pilot/Commercial/Production = blocked
```

## ما أنجزته الحزمة

- Payload محدود لسبعة ملفات React فقط.
- لا FastAPI patch ولا backend ولا route جديد.
- شاشة بداية عربية بملخص حالة وحدود واضحة.
- Sidebar مكتبي وDrawer للهاتف.
- مكونات عرض قابلة لإعادة الاستخدام لتقليل تكرار JSON/raw data.
- بطاقات للمساعدين والمساحات وحالات حجب صريحة.
- Build validator وطبقات توثيق/trace/hashes.

## نتائج التحقق المنفذة في بيئة المرشح

```text
NPM_CI_IGNORE_SCRIPTS = PASS
TSC_NO_EMIT = PASS
VITE_BUILD = PASS
TARGET_FILES = 7
SOURCE_PROJECT_MUTATION = NONE
RUNTIME_UAT = NOT_EXECUTED
```

## حدود لا يجوز تجاوزها

```text
NO_REACT_WRITE_UI
NO_AUTHORIZATION_OR_BEARER_TOKEN
NO_LOCALSTORAGE_OR_SESSIONSTORAGE
NO_SQLITE_MIGRATION
NO_BACKEND_OR_FASTAPI_CHANGE
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_COMMERCIAL_CLIENT_SCOPE_APPLY
NO_PRODUCTION
```

## معاينات

`VISUAL_PREVIEWS/` هي mock/source-derived فقط. لا تساوي screenshot من runtime. يلزم UAT Windows لاحق إن تم Apply.

## الملفات الرئيسية

- `PATCH_MANIFEST.json`
- `PREIMAGE_SHA256.json` / `POSTIMAGE_SHA256.json`
- `UX_UI_DISCOVERY_AND_DESIGN_REPORT_AR.md`
- `READ_ONLY_CONTRACT_AND_NEGATIVE_MATRIX_AR.md`
- `WINDOWS_READ_ONLY_PRODUCT_UAT_RUNBOOK_AR.md`
- `ERROR_RECORD_20260706_PRODUCT_START_SCREEN_CANDIDATE.md`
- `NEXT_AUTHORIZATION_AFTER_PRODUCT_CANDIDATE_REVIEW_AR.md`

## الخطوة التالية

لا تنفذ Apply تلقائيًا. بعد مراجعة الشكل، يلزم أحد التفويضين الحرفيين الموجودين في ملف `NEXT_AUTHORIZATION...`.
