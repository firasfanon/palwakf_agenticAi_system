# دليل تشغيل المرشح التنفيذي

1. نفذ `Invoke-UnifiedGovernedCapabilityFoundationReadiness.ps1` فقط للحصول على Syntax + Preflight + WhatIf.
2. لا تستخدم `Install-UnifiedGovernedCapabilityFoundationV1.ps1 -Apply` إلا بعد تفويض Apply مستقل.
3. بعد Apply نفذ `Test-UnifiedGovernedCapabilityFoundationPostApply.ps1`.
4. لا ينفذ MB6 نموذجًا. تشغيل Pilot يتطلب نشاط تفويض مستقل بعد نجاح UAT.
