# Error Record — HAR Filename Reconciliation V1

## السبب

أظهر Evidence Archive المقبول أن Edge حفظ HAR باسم `127.0.0.1.har` بينما Runner كان يبحث حصريًا عن `browser_network.har`.

## ما فشل

Runner أصدر `PARTIAL_ACCEPTANCE__HTTP_AND_RENDER_CAPTURE_PASS__HAR_PENDING` رغم وجود HAR صالح داخل Evidence Root.

## العلاج

- اكتشاف مباشر فقط لملفات `*.har` في جذر Evidence Root.
- اعتماد اسم قياسي أولًا.
- reconcile لملف واحد فقط.
- رفض تعدد الملفات ورفض HAR غير صالح عبر بوابات موجودة.

## آخر baseline مستقر

`READ_ONLY_REACT_RUNTIME_UAT_ACCEPTED_BY_EVIDENCE_RECONCILIATION` بتاريخ 2026-07-04.
