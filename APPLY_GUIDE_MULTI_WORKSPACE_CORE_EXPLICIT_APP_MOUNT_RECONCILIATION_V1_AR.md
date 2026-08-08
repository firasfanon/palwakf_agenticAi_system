# دليل التطبيق العربي — Multi-Workspace Core Explicit App Mount Reconciliation V1

## طبيعة الإجراء
هذا إصلاح محصور في `app.py` فقط. لا يعيد نسخ أي من ملفات Workspace Core؛ بل يربط المصدر الموجود والمطابق للعقد بمسار FastAPI.

## قبل التطبيق
- نفّذ Syntax Gate وPreflight وWhatIf فقط.
- لا تطبق إن فشل `PRECONDITION_WORKSPACE_CORE_SOURCE_HASHES=PASS`.
- لا تطبق إذا كان `WORKSPACE_CORE_IMPORT_ABSENT=FAIL` أو `WORKSPACE_CORE_MOUNT_ABSENT=FAIL`.
- أوقف Uvicorn قبل التطبيق الفعلي، ثم شغله من جديد بعده.

## التطبيق الفعلي
لا يتم إلا بعد تفويض Apply منفصل. ينشئ Installer نسخة preimage لـ`app.py` وmanifest داخل:
`backups/multi_workspace_core_explicit_app_mount_reconciliation_v1_<timestamp>/`

## ما لا يفعله
- لا ينشئ `audit/workspace_core.sqlite` أثناء التطبيق.
- لا ينشئ مساحة تخزين لأي Workspace.
- لا ينقل بيانات Governed Operations.
- لا يغير Command Center.
- لا يشغل نموذجًا أو Pilot أو أدوات تنفيذ.
