# تشغيل الماسحات الخارجية بنطاق مشروع محكوم — Wave 2 V1

## المسار اليومي

`/agent-console/security-scans`

يستخدمه المشغل لإنشاء مهمة فحص، مراجعتها، اعتمادها، تشغيلها، ثم مراجعة النتيجة.

## صفحات الحوكمة

- `/agent-console/security-scans/governance`
- `/agent-console/security-scans/manifests`
- `/agent-console/security-scans/evidence`

## Semgrep

- Admission مقبول.
- Quality Baseline معتمد.
- قواعد محلية فقط.
- لا Remote Rules.
- لا Autofix.
- لا Source Write.

## Gitleaks

- Admission مقبول.
- Quality Baseline معتمد.
- حجب قيم الأسرار.
- لا Git mutation.
- لا حفظ للمخرجات الخام.

## Trivy

يبقى في `READINESS_HOLD` حتى اعتماد قاعدة ثغرات Offline، منشئها، بصمتها، سياسة تحديثها، وفترة صلاحيتها.

## الحدود

لا Model inference، لا Shell، لا Git، لا Network، لا Source Write، لا Automatic Retry، ولا تشغيل دون موافقة بشرية.
