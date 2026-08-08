# دليل تشغيل إصلاح Empty-Collection Binding

## نطاق التنفيذ

هذا Runner يكتب أدلة Baseline في `%TEMP%` فقط. لا يكتب داخل مجلد المشروع ولا يحتوي على `Apply`.

## شرط النجاح

```text
CANDIDATE_SYNTAX_RESULT=PASS
CANDIDATE_EMPTY_COLLECTION_BINDING_GUARD=PASS
RUNTIME_EMPTY_COLLECTION_FIRST_APPEND=PASS
RUNTIME_FIXTURE_SELF_TEST=PASS
BASELINE_RESULT=PASS
WHATIF_STATUS=COMPLETE
FINAL_BASELINE_RUNNER_RESULT=PASS
PROJECT_MUTATION=NONE
```

## عند الفشل

يتوقف Runner عند المرحلة الفاشلة. لا تعيد تشغيل الحزمة القديمة ولا تنشئ Baseline يدويًا من سكربت منفرد.
