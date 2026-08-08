# دليل تطبيق Command Center V1.2 Rev C

## شرط سابق
Command Center V1.1 Rev B مطبق، واختبارات الوحدة وRoute Probe ناجحة.
لا تطبق هذا الإصلاح لمعالجة أخطاء مصدر حقيقية؛ هذا الإصلاح مخصص فقط لإيجابية كاذبة من `__pycache__`.

## بوابات قبل التطبيق
1. `Test-CommandCenterV1RevCStaticGateSyntax.ps1`
2. `Test-CommandCenterV1RevCStaticGatePreflight.ps1`
3. `Install-CommandCenterV1RevCStaticGateHotfix.ps1 -WhatIf`

## التطبيق
بعد تفويض مستقل فقط:
`Install-CommandCenterV1RevCStaticGateHotfix.ps1 -PackageRoot <package> -ProjectRoot <project> -Mode Upgrade`

## القبول
- `INSTALL_STATUS=COMPLETE`
- `BACKUP_STATUS=COMPLETE`
- `STATIC_GATE_SCAN_SCOPE=TEXT_SOURCE_ONLY`
- `PY_CACHE_EXCLUSION=ACTIVE`
- `FINAL_RESULT=PASS`
- إعادة تشغيل UnitTest وRuntime Probe السابقين بلا تعديل.
