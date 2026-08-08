# Error Record

## Environment Qualification Gap

- **السبب:** بيئة التحقق المتاحة استخدمت Python 3.13.5 بينما المشروع يعلن `>=3.11,<3.13`.
- **الملفات المتأثرة:** لا ملفات تطبيق؛ التأثير على صلاحية اعتماد بيئة الاختبار فقط.
- **ما نجح:** Preimage/Postimage، 26/26 UAT، و65/65 backend tests في Replica معزولة.
- **ما لا يمكن ادعاؤه:** توافق Python 3.12.10 لم ينفذ من هذه البيئة.
- **الحل:** تنفيذ `Run-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1` محليًا عبر `.venv\Scripts\python.exe` ثم حفظ Evidence Archive.
- **آخر baseline مستقر:** `ISOLATED_REPLICA_ACCEPTED__WINDOWS_PYTHON_3_12_10_CONFIRMATION_PENDING`.

## Warnings

ظهرت 54 تحذير Deprecation متعلقًا بـFastAPI `on_event("startup")`. لا تؤثر في نتيجة الاختبارات، لكنها دين توثيقي لترحيل منفصل إلى lifespan handlers.
