# Run Guide

1. تحقق من SHA-256.
2. شغّل `Invoke-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryReadiness.ps1`.
3. لا تستخدم `-Apply` قبل تفويض مستقل.
4. بعد Apply، شغّل `Test-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryPostApply.ps1`.

الاختبار الموجب للإنتاج لا يبدأ قبل Provisioning مستقل لممثلين موقّعين/مفاتيح Bearer محلية مجزأة.
