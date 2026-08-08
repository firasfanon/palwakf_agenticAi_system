# Error Record — Windows UAT Runner Compatibility V3

- **السبب:** Windows PowerShell 5.1 يقيّم القيم الافتراضية لـ`param` قبل تهيئة `$PSScriptRoot` في هذا السياق؛ كما أن V2 استدعى `.Count` على نتيجة Parser قد تكون مفردة مع `Set-StrictMode`.
- **الملفات المتأثرة:** Runner، Static Gate، وأداة Repair V2.
- **ما فشل:** V1 Parser، ثم Path resolution، ثم `.Count` في V2.
- **العلاج:** V3 يحل المسارات بعد بدء التنفيذ، ويحول نتائج Parser إلى عدّ صحيح دون افتراض collection، ويشحن payload كاملًا.
- **Baseline مستقر:** React Lock/Build/HTTP UAT baseline 20260703؛ Windows browser evidence ما زال pending.
