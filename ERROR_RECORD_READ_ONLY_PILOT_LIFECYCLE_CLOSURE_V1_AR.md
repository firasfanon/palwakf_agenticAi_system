# Error Record — Lifecycle Closure V1.2 Rev C

## ER-PLC-001: Installer reported a backup path without materializing a backup
- **الحالة:** مغلق في Rev B.
- **الحل:** Backup preimage + `install_preimage_manifest.json`.

## ER-PLC-002: Deterministic Evals hung without stdout/stderr
- **الدليل:** تشغيل `Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1` تجاوز 90 ثانية؛ child process أوقف قسرًا، ولم تطبع العملية أي مخرجات أو أخطاء.
- **السبب الجذري المثبت:** السطر `Copy-Item -LiteralPath $tempRoot -Destination $badRoot -Recurse -Force` حيث كان `$badRoot = Join-Path $tempRoot 'bad'`. نسخ المصدر إلى descendant منه يولّد شجرة نسخ متداخلة `bad\bad\...`.
- **الملف المتأثر:** `scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1`.
- **ما فشل:** افتراض أن fixture سلبي داخل root المؤقت آمن مع `Copy-Item -Recurse`.
- **الحل في Rev C:** sibling temporary root مستقل، guard يمنع أي destination تحت `$tempRoot`، copy لمحتويات المصدر فقط، وcleanup مضبوط.
- **آخر baseline مستقر:** `PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_SAPF_V1_2026_06_27` + `LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1=PASS`.
