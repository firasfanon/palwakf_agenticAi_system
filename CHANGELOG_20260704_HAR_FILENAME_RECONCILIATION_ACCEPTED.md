# Changelog — 2026-07-04
## HAR Filename Reconciliation V1

### Applied locally and accepted
- تطبيق `Repair-HarFilenameReconciliationV1.ps1` على مشروع Windows.
- النسخ الاحتياطي أُنشئ محليًا قبل التعديل.
- نجاح فحص Parser للـRunner والـStatic Gate.
- نجاح Static Gate بما في ذلك:
  - `runner_has_har_filename_reconciliation=True`
  - `runner_rejects_ambiguous_har_evidence=True`
  - `FINAL_RESULT=PASS`

### لم يتغير
- لا React write.
- لا FastAPI write.
- لا نموذج أو Pilot.
- لا قاعدة بيانات.
- لا تغيير منصة أو Production promotion.

### الأثر
تم إغلاق فجوة اسم HAR في Runner المستقبلي فقط. الدليل السابق للـBrowser Runtime remains accepted بالـEvidence Reconciliation.
