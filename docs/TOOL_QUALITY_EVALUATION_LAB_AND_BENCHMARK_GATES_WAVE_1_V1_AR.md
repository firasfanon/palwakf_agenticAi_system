# مختبر تقييم جودة الأدوات وبوابات القياس — الموجة الأولى V1

## الغرض

الانتقال من «الأداة موجودة ومقبولة» إلى «الأداة مختبرة ومقاسة ولها Baseline معتمد بشريًا».

## النطاق

- Fixtures اصطناعية فقط.
- Golden Results ثابتة.
- قياس الدقة والحتمية والخصوصية.
- Safety Gate أعلى من النتيجة الرقمية.
- مراجعة بشرية قبل اعتماد Baseline.
- حجر تلقائي عند فشل بوابة الأمان.

## الأدوات

- عقود الفهرسة المحلية.
- Telemetry المحلية.
- Tree-sitter readiness.
- OpenTelemetry local quality.
- Semgrep fixture scan.
- Gitleaks synthetic-secret scan.
- Trivy offline readiness.
- مراجعة الأدوات المؤجلة بلا تشغيل.

## الحدود

لا فحص للمشروع الحي، لا تنزيل، لا تثبيت، لا Shell، لا Git، لا Model inference، لا Autofix، لا شبكة، ولا Automatic Retry.
