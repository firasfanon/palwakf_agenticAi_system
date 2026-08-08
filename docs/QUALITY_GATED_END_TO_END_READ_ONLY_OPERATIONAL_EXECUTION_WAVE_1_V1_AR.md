# التشغيل القرائي الكامل المحكوم بالجودة — Wave 1 V1

## الاتجاه التشغيلي

الشاشة الرئيسية مصممة للمستخدم اليومي: إنشاء مهمة، مراجعتها، تشغيلها، ثم مراجعة النتيجة.

نُقلت التفاصيل الثقيلة إلى صفحات فرعية:

- `/agent-console/operations/governance`
- `/agent-console/operations/manifests`
- `/agent-console/operations/evidence`

## دورة المهمة

`DRAFT → READY_FOR_REVIEW → APPROVED_FOR_READ_ONLY_RUN → RUNNING → HUMAN_RESULT_REVIEW → ACCEPTED_RESULT`

ولا يوجد تشغيل أو قبول نتيجة تلقائي.

## الأدوات الأصلية

Project Summary، Route Index، Component Index، Symbol Index، Docs Index، File Metadata، Project Reader، Route Reader.

كلها قرائية داخل نطاق المشروع، وتتطلب Baseline جودة مقبولًا.

## الحدود

لا Model inference، لا Shell، لا Git، لا شبكة، لا كتابة مصدر، لا Automatic Retry، لا Self-Apply.
