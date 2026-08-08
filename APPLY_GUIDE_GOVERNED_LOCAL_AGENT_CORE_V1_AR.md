# دليل التطبيق — Governed Local Agent Core V1

## طبيعة الدفعة

دفعة تطوير تأسيسية كبيرة للوكلاء المحليين المحكومين. التطبيق يضيف Module جديدًا واختبارًا واحدًا وتعديلًا صريحًا واحدًا إلى `app.py`. لا يُشغّل نموذجًا محليًا ولا ينفذ Pilot.

## التسلسل الإلزامي

1. Candidate Syntax.
2. Preflight فقط.
3. WhatIf فقط.
4. تفويض Apply مستقل.
5. Post-Apply Technical Verification.
6. Runtime Negative UAT منفصل ومصرح به.

## أوامر Candidate Syntax + Preflight

```powershell
& "$package\scripts\Test-GovernedLocalAgentCoreV1CandidateSyntax.ps1" -PackageRoot $package -ProjectRoot $target
& "$package\scripts\Test-GovernedLocalAgentCoreV1Preflight.ps1" -PackageRoot $package -ProjectRoot $target
```

ينتج Preflight مسار `PREFLIGHT_MANIFEST`. استخدمه لاحقًا مع installer و`-WhatIf` فقط.

## إصلاح Candidate Runtime Preflight

هذه الحزمة تحل محل Candidate V1 الأصلي بسبب خلل PowerShell داخل Script الـPreflight. لا تستخدم الحزمة الأصلية. ابدأ من Candidate Syntax في هذه الحزمة؛ سيجري الفحص الآن Runtime smoke آمنًا داخل `%TEMP%` قبل الـPreflight الحقيقي.
