# دليل التشغيل

هذه الحزمة تتطلب تشغيل `Readiness` قبل أي Apply. لا تستخدم `Install-FinalConsolidatedExecutionCarrier.ps1 -Apply` إلا بعد تفويض Apply مستقل ومخرجات WhatIf ناجحة.

تدقيق المرشح يشمل:
- جرد البصمات.
- Parser Windows PowerShell.
- اختبار Scanner للنطاقات الصحيحة والخطرة.
- عقد الحدّ الصلاحي وإعداد default-deny.

Post-Apply UAT يثبت الحالة الساكنة، رفض عدم المصادقة على Runtime، وانتهاء Uvicorn. لا يثبت دخول مستخدم حقيقي بين المساحات لأن هذا المرشح لا يخلق Actors أو Tokens.
