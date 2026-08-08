# بوابات القبول

## G0 — Candidate Integrity

- تطابق hashes للـpreimage.
- جميع الملفات الجديدة متوقعة الغياب.

## G1 — Apply Scope

- التغيير محصور في `backend/tests` و`scripts`.
- لا تغيير في `backend/src` أو `frontend` أو `config` الإنتاجي.

## G2 — Static Gate

- `python -m py_compile` لملفات الاختبار الجديدة/المعدلة.
- Fixture موسوم `test_only` و`production_provisioning=FORBIDDEN`.
- لا يوجد `/pilot/execute` في positive UAT.

## G3 — Targeted UAT

- `test_legacy_write_authorization_negative_uat.py` يمر.
- `test_legacy_write_authorization_positive_uat.py` يمر.

## G4 — Full Suite

- `65 passed / 0 failed` أو نتيجة أحدث موثقة بلا failures.

## G5 — Evidence / Handoff

- archive + SHA-256.
- Baseline/Handoff/Changelog/Error Record محدثة بعد قبول Apply حقيقي.

فشل أي بوابة يبقي React write وPilot وProduction محظورة.
