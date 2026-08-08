# Baseline محدث — Local Agents
## PalWakf Local Agents | Accepted Baseline | 2026-06-27
### إضافة: Read-Only Pilot Lifecycle Closure V1.2 Rev C

> هذا الملف تحديث Baseline بعد تطبيق ناجح. لا يبدل الـCore Runtime أو عقد الـ11 سطرًا.

## 1) هوية Baseline

```text
BASELINE_ID=PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_LIFECYCLE_CLOSURE_REVC_2026_06_27
PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
SCOPE=LOCAL_AGENTS_ONLY
BASELINE_STATUS=ACCEPTED_FOR_READ_ONLY_PILOTS
```

## 2) الحزم المغلقة المعتمدة

```text
PACK01=ACCEPTED_AND_CLOSED
STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1=APPLIED_ACCEPTED_AND_CLOSED
READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1_2_REVC=APPLIED_ACCEPTED_AND_CLOSED
```

## 3) الحدود الثابتة

```text
AUTONOMY=L0_READ_ONLY
HUMAN_REVIEW_REQUIRED=YES
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
MODEL_EXECUTION=DISABLED_BY_DEFAULT
ONE_PILOT_AT_A_TIME=YES
```

## 4) Lifecycle Closure capability

الملفات المعتمدة داخل المشروع:

```text
scripts\New-ReadOnlyPilotHumanReviewDecisionV1.ps1
scripts\Archive-ReadOnlyPilotAfterHumanReviewV1.ps1
scripts\Test-ReadOnlyPilotActiveStateV1.ps1
scripts\Test-ReadOnlyPilotLifecycleClosureV1.ps1
scripts\Test-ReadOnlyPilotLifecycleClosurePackageSyntaxV1.ps1
scripts\Test-ReadOnlyPilotLifecycleClosurePreflightV1.ps1
scripts\Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1
task_contracts\READ_ONLY_PILOT_HUMAN_REVIEW_DECISION_V1.json
governance\read_only_pilot_lifecycle_closure\READ_ONLY_PILOT_HUMAN_REVIEW_AND_ARCHIVE_POLICY_V1.md
governance\read_only_pilot_lifecycle_closure\DECISION_RECORD_CONTRACT_V1.md
```

### الانتقال المعتمد

```text
APPROVED_FOR_READ_ONLY_RUN
  -> evidence-constrained execution
  -> PENDING_HUMAN_REVIEW
  -> Human Review Decision
  -> archive-only transition
  -> tasks\archived
```

### الضمانات

- لا تنشأ Human Review Decision تلقائيًا.
- لا تتم الأرشفة بلا Decision Record صالح ومراجع تشغيل/أدلة متطابقة.
- لا تحذف Raw أو Canonical أو Report أو Evidence Manifest أثناء الأرشفة.
- فحص الحالة النشطة يرفض بقاء حالات `APPROVED_FOR_READ_ONLY_RUN` أو `RUNNING` قبل تفعيل Pilot جديد.

## 5) قبول Rev C

```text
INSTALL_STATUS=COMPLETE
BACKUP_STATUS=COMPLETE
REVC_BACKUP_MANIFEST_EXISTS=YES
REVC_INSTALLED_SOURCE_GUARD=PASS
LIFECYCLE_STATIC_GATE=PASS
LIFECYCLE_EVALS=PASS_6_OF_6
SAPF_REGRESSION=PASS_6_OF_6
PACK01_REGRESSION=PASS_5_OF_5
```

## 6) Error Record

سجل خطأ Rev B مغلق:

```text
ERROR_ID=PLC_REVB_EVAL_RECURSIVE_DESCENDANT_COPY
ROOT_CAUSE=Copy-Item copied temp root into a child directory
FIX=Rev C uses sibling temporary root + containment guard + stage markers
STATUS=CLOSED_BY_REVC
```

### ملاحظة Harness

```text
ERROR_ID=POST_APPLY_EXTERNAL_WRAPPER_EMPTY_EXITCODE
SCOPE=External verification wrapper only
IMPACT=Produced false diagnostic after a successfully completed evaluator
EVIDENCE=Captured stdout confirms EVAL_PASSED_COUNT=6 and FINAL_RESULT=PASS
PROJECT_CODE_MUTATION=NONE
STATUS=DOCUMENTED
```

## 7) الحالة التشغيلية الحالية

```text
EXISTING_PILOT=PILOT_READ_ONLY_CONTEXT_EVIDENCE_001
EXISTING_PILOT_STATE=EXECUTED_PENDING_HUMAN_REVIEW
NEW_PILOT=SAPF_DOCUMENTATION_HANDOFF_PILOT_001
NEW_PILOT_STATE=PENDING_HUMAN_APPROVAL
NEW_PILOT_APPROVAL=BLOCKED_UNTIL_EXISTING_PILOT_CLOSURE
```

## 8) الخطوة التالية المصرح بها

التسلسل التالي فقط:

1. إنشاء Human Review Decision للمهمة القديمة `PILOT_READ_ONLY_CONTEXT_EVIDENCE_001`.
2. أرشفتها عبر `Archive-ReadOnlyPilotAfterHumanReviewV1.ps1`.
3. تشغيل `Test-ReadOnlyPilotActiveStateV1.ps1` وإثبات صفر حالات `APPROVED_FOR_READ_ONLY_RUN` أو `RUNNING`.
4. عندها فقط مراجعة مهمة `SAPF_DOCUMENTATION_HANDOFF_PILOT_001` للقرار البشري التالي.

لا يتم تشغيل Ollama أو `-Execute` للمهمة الجديدة في هذه المرحلة.
