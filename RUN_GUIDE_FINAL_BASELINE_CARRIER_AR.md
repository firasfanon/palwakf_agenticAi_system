# دليل تشغيل Final Baseline Carrier

## هذا التشغيل لا يغير المشروع

شغّل `Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineRunner.ps1` فقط. هو ينفذ فحصًا نحويًا، ثم اختبار Runtime مستقل ببيئة مؤقتة، ثم Baseline للمشروع، ثم WhatIf.

## نجاح مقبول

```text
CANDIDATE_SYNTAX_RESULT=PASS
RUNTIME_FIXTURE_SELF_TEST=PASS
BASELINE_RESULT=PASS
WHATIF_STATUS=COMPLETE
FINAL_BASELINE_RUNNER_RESULT=PASS
PROJECT_MUTATION=NONE
```

## فشل

إذا فشلت أي مرحلة، يتوقف Runner قبل المرحلة التالية. لا يوجد Apply في الحزمة ولا يوجد أمر استعادة مطلوب لأن المشروع لا يتغير.
