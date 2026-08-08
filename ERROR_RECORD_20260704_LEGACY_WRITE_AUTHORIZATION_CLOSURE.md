# Error Record — Legacy Write Authorization Closure V1

## ER-LWA-001 — Scope drift في حامل الـCandidate

- **السبب:** `PATCH_PAYLOAD` الأصلي احتوى ملفات `__pycache__/*.pyc`، بينما manifest أعلن سبعة ملفات مصدر فقط.
- **الملفات المتأثرة:** Apply carrier الأصلي و`PATCH_PAYLOAD/**/__pycache__`.
- **ما فشل:** تطبيق الحامل الأصلي كان سيضيف binary artifacts غير مصرح بها، ولا يتحقق من preimage hashes.
- **الحل:** حامل تطبيق جديد ينسخ قائمة manifest الموقعة فقط، يرفض hash mismatch، وينشئ Backup/rollback manifest.
- **آخر baseline مستقر:** `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260704_HAR_FILENAME_RECONCILIATION_ACCEPTED`.

## ER-LWA-002 — Negative UAT غير صالح لقياس عدم mutation

- **السبب:** الاختبار الأصلي افترض عدم وجود أي SQLite بعد تركيب modules، في حين أن mounting/initialization يكوّن SQLite bootstrap state قبل الطلب.
- **الملفات المتأثرة:** `backend/tests/test_legacy_write_authorization_negative_uat.py`.
- **ما فشل:** 17 assertions كاذبة رغم عودة HTTP codes الصحيحة.
- **الحل:** Snapshot hashes بعد startup وقبل الطلب، ثم مقارنة الحالة بعد الطلب؛ مع تغطية `POST /api/tasks` و`run` وبقية 15 route و10 edge cases.
- **النتيجة:** `25 passed`.

## ER-LWA-003 — Regression tests غير محدثة للعقد الجديد

- **السبب:** 16 اختبارًا قائماً تفترض write بلا Bearer أو تستدعي مسارات Legacy غير workspace-scoped أو تتحقق من UI marker قديم.
- **الحل:** مؤجل لدفعة Test Contract Migration مستقلة. لا يتم تخفيف Boundary كي ينجح الاختبار القديم.
- **آخر baseline:** هذا التسليم بحالة targeted acceptance فقط، ولا يمثل full regression certification.
