# Guide Update Snippet

## Local Agents — Legacy Test Contract Migration + Controlled Positive Authorization UAT V1

- ثبت أن طبقة Legacy write authorization ترفض السيناريوهات السلبية (25 حالة) وتسمح بكتابة محكومة داخل Fixtures مؤقتة فقط (حالة إيجابية واحدة).
- ترحيل اختبارات Legacy يقتصر على اختبارات وUAT carriers؛ لا تعديل على `backend/src`.
- القبول الحالي: Replica معزولة. يلزم تأكيد Windows/Python 3.12.10 قبل اعتماد التطبيق المحلي.
- تبقى واجهة React في وضع read-only، ولا تشغيل نموذج أو Pilot أو مسار تجاري.
