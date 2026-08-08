# Changelog — 2026-07-04

## HAR Filename Reconciliation V1

- أضيف `Resolve-HarEvidence` إلى Windows Local Browser UAT Runner.
- يطبع Runner الآن `browser_network_har_resolution.json` ضمن أرشيف الأدلة.
- عند وجود اسم `browser_network.har`، يستعمله مباشرة.
- عند غياب الاسم القياسي ووجود ملف HAR واحد فقط في جذر Evidence Root، ينسخه إلى الاسم القياسي ثم يحلله.
- عند تعدد ملفات HAR، يفشل بقصد عبر `HAR_FILENAME_AMBIGUOUS`.
- أضيفت checks ساكنة لتأكيد reconciliation ورفض الغموض.
- لا تغيرات في React أو FastAPI أو package-lock أو سياسة read-only.
