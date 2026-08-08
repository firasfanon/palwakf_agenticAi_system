# سياسة Structured Analysis Payload Foundation V1

## الغرض
توفير مخرج تحليلي متخصص وقابل للتحقق لدوري `knowledge_researcher` و`documentation_handoff`، مع إبقاء Core Runtime وعقد المخرجات ذي 11 سطرًا دون تغيير.

## حدود الحزمة
```text
AUTONOMY=L0_READ_ONLY
RUNTIME_MODE=read_only_report_only
HUMAN_REVIEW_REQUIRED=YES
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
NETWORK_WRITE=NONE
```

## ما يتغير
- Contract JSON مستقل لكل Role.
- Validator مستقل للـPayload.
- Runner مستقل لا يستخدم أو يعدل Runner الـCore المجمد.
- ملفات Charter وOutput Profile وPilot Template.
- Evals حتمية لقبول/رفض الـPayload.
- Registry admission ضيق: إضافة skill `documentation_handoff` فقط لدور `documentation_handoff` مع بقاء L0/read-only.

## ما لا يتغير
- `runtime\ReadOnlyRuntimeContextEvidenceV1.psm1`
- `scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1`
- `scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1`
- `task_contracts\MODEL_OUTPUT_CONTRACT_V1.json`
- لا يوجد تشغيل Model أو Task generation أثناء التثبيت أو التحقق أو الـEvals.

## قبول أي Model Run لاحق
لا يبدأ `-Execute` إلا لمهمة موجودة في `tasks\approved` بحالة `APPROVED_FOR_READ_ONLY_RUN`، مع أدلة محلية معتمدة ونجاح البوابات المطلوبة. يبقى الناتج `PENDING_HUMAN_REVIEW` فقط.
