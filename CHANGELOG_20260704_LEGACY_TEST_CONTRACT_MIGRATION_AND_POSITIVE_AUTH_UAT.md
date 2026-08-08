# Changelog

## Added
- `backend/tests/conftest.py`: Fixture registry مؤقت ومحصور بالاختبار.
- `backend/tests/test_legacy_write_authorization_positive_uat.py`: إثبات كتابة مصرح بها ضمن مشروع disposable.
- Static Gate وRunner لعملية Windows المعزولة.

## Changed
- ترحيل أربعة اختبارات Legacy لعقود Authorization وWorkspace وActor الحالية.

## Verified
- Preimage/Postimage: PASS.
- Targeted Negative + Positive UAT: 26/26 PASS.
- Full backend suite: 65/65 PASS.
- `backend/src` hash equality against prior applied source: PASS.

## Not changed
- لا production source.
- لا React write أو Pilot أو Model execution أو Commercial UAT.
