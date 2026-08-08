# الترحيل من Operational Activation Foundation V1

## المتطلب السابق
يجب أن تكون الدفعة السابقة مثبتة وأن يكون فحصها وEvalsها ناجحين.

## لا تستبدل Runner V1
هذه الدفعة تضيف Runner جديداً باسم:

```text
Invoke-ReadOnlyContextEvidenceRunnerV1.ps1
```

ويبقى Runner السابق كما هو لأغراض المقارنة والتراجع.

## الترتيب الصحيح
1. تثبيت هذه الدفعة في وضع Upgrade.
2. تنفيذ الفحص الساكن الجديد.
3. تنفيذ تقييمات السياق والأدلة فقط.
4. إنشاء Pilot غير حساس في inbox.
5. اعتماده يدوياً عبر Gate الموجود سابقاً.
6. Dry Run وبناء Evidence Manifest.
7. مراجعة بشرية للـManifest.
8. استدعاء Ollama فقط بعد اعتماد صريح منفصل.
