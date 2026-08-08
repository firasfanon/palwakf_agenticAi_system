# Error Record — 2026-07-04
## HAR Filename Reconciliation

| الحقل | القيمة |
|---|---|
| السبب | Edge حفظ HAR باسم `127.0.0.1.har` بدل الاسم الذي انتظره Runner: `browser_network.har`. |
| الأثر السابق | أعاد Runner حالة `HAR_PENDING` رغم وجود HAR صالح في أرشيف الأدلة. |
| الحل | قبول الاسم القياسي أولًا، ثم تسوية ملف HAR وحيد بديل، مع رفض وجود أكثر من ملف HAR. |
| التحقق | تطبيق محلي وStatic Gate: `FINAL_RESULT=PASS`. |
| آخر baseline مستقر | `READ_ONLY_REACT_RUNTIME_UAT_ACCEPTED` مع HAR Filename Reconciliation V1. |
| لم يُنفذ | إعادة Browser UAT أو Model/Pilot أو React write. |
