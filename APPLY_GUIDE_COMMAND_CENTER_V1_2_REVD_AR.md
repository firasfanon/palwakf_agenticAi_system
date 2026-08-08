# دليل تطبيق Command Center V1.2 Rev D

## نطاق التغيير
Static Gate فقط. لا تغييرات تشغيلية على التطبيق.

## بوابات قبل التطبيق
1. Syntax Gate
2. Preflight
3. Static Gate Eval (3 حالات)
4. Installer WhatIf

## التطبيق
بعد تفويض منفصل فقط:
`Install-CommandCenterV1RevDStaticGatePrecisionHotfix.ps1 -PackageRoot <package> -ProjectRoot <project> -Mode Upgrade`

## قبول ما بعد التطبيق
- `INSTALL_STATUS=COMPLETE`
- `BACKUP_STATUS=COMPLETE`
- `GENERIC_STRING_REPLACE_TREATMENT=NON_MUTATING_EXCLUDED`
- `FINAL_RESULT=PASS`
- إعادة `unittest` وRuntime Probe والاحتفاظ بـ`MODEL_EXECUTION=NONE`, `PILOT_EXECUTION=NOT_EXECUTED`.
