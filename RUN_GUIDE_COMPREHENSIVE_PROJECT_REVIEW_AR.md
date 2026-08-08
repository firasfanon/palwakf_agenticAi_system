# تشغيل حزمة إصلاح بناء التقرير

1. نفذ فحص الحزمة `Test-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1PackageSyntax.ps1`.
2. يجب أن ينجح `CANDIDATE_REPORT_CONSTRUCTION_RUNTIME_SELF_TEST=PASS`.
3. نفذ `Invoke-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1.ps1` مع `PackageRoot` و`ProjectRoot`.
4. التدقيق قراءة فقط وينشئ الأدلة في `%TEMP%` فقط.
