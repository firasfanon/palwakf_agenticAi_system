# ملف توريث شامل — Local Agents
## PalWakf Local Agents | Lifecycle Closure Rev C | 2026-06-27

## 1) نقطة الاستئناف

```text
LOCAL_PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
CURRENT_ACCEPTED_BASELINE=PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_LIFECYCLE_CLOSURE_REVC_2026_06_27
CORE_RUNTIME=FROZEN
EXECUTION_DEFAULT=disabled
AUTONOMY=L0_READ_ONLY
HUMAN_REVIEW_REQUIRED=YES
```

## 2) ما تم إغلاقه

1. Pack 01 Read-only Analysis.
2. Structured Analysis Payload Foundation V1.
3. Read-only Pilot Lifecycle Closure V1.2 Rev C.

## 3) أهم دليل Rev C

```text
INSTALL_STATUS=COMPLETE
BACKUP_STATUS=COMPLETE
BACKUP_MANIFEST=install_preimage_manifest.json
REVC_INSTALLED_SOURCE_GUARD=PASS
LIFECYCLE_STATIC=PASS
LIFECYCLE_EVALS=PASS_6_OF_6
SAPF_REGRESSION=PASS_6_OF_6
PACK01_REGRESSION=PASS_5_OF_5
```

## 4) سبب وجود Rev C

Rev B contained a recursive test-fixture copy into a descendant of its own temp root. This caused a timeout. Rev C fixes it using an external sibling temporary root, containment guard, stage markers, and cleanup. The actual Rev C evaluator successfully completed all six deterministic cases.

## 5) الحالة الحالية للمهمات

### Pilot القديم

```text
TASK_ID=PILOT_READ_ONLY_CONTEXT_EVIDENCE_001
AGENT=coordinator
EVIDENCE_STATE=EXECUTED_PENDING_HUMAN_REVIEW
TASK_FILE_STATUS=APPROVED_FOR_READ_ONLY_RUN
```

تشغيله مثبت: model output صحيح، 11 سطرًا، دون trailing text، وHost-owned envelope، وEvidence Manifest `EVD-001`.

### Pilot الجديد

```text
TASK_ID=SAPF_DOCUMENTATION_HANDOFF_PILOT_001
AGENT=documentation_handoff
STATUS=PENDING_HUMAN_APPROVAL
RISK=LOW
AUTONOMY=L0_READ_ONLY
```

**ممنوع** نقله إلى `tasks\approved` أو تشغيله قبل إغلاق المهمة القديمة.

## 6) بروتوكول الاستئناف

### قبل أي Human Review Decision

1. شغّل:
   - `Test-ReadOnlyPilotLifecycleClosureV1.ps1`
   - `Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1`
   - `Test-StructuredAnalysisPayloadFoundationV1.ps1`
   - `Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1`
   - `Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1`
   - `Test-ReadOnlyAnalysisPack01V1_3.ps1`
   - `Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1`

2. تأكد من:
```text
FINAL_RESULT=PASS
LIFECYCLE_EVAL_FAILED_COUNT=0
SAPF_EVAL_FAILED_COUNT=0
PACK01_EVAL_FAILED_COUNT=0
```

### بعد قرار المراجعة البشرية الصريح

3. استخدم `New-ReadOnlyPilotHumanReviewDecisionV1.ps1` لتوثيق القرار فقط.
4. استخدم `Archive-ReadOnlyPilotAfterHumanReviewV1.ps1` للأرشفة فقط.
5. شغّل `Test-ReadOnlyPilotActiveStateV1.ps1`.
6. لا تنتقل للمهمة الجديدة قبل إثبات أن لا توجد حالة:
```text
APPROVED_FOR_READ_ONLY_RUN
RUNNING
```

## 7) محظورات ثابتة

```text
NO_PLATFORM_SCOPE
NO_DB_SCOPE
NO_GIT_WRITE
NO_DEPLOYMENT
NO_SECRET_READ
NO_MEMORY_PROMOTION
NO_AUTO_APPROVAL
NO_AUTO_ARCHIVE
NO_NEW_MODEL_RUN_UNTIL_OLD_PILOT_CLOSED
```

## 8) Error Record مبسط

| Error | Cause | Status |
|---|---|---|
| Rev B Evals timeout | Recursive descendant temp-root copy | Closed by Rev C |
| Empty `ExitCode` in external timeout wrapper | Harness process object did not expose exit code reliably | Documented; underlying eval succeeded from captured stdout |

## 9) لا توجد أعمال غير مغلقة من Rev C

```text
REV_C_PACKAGE=APPLIED_ACCEPTED_AND_CLOSED
HUMAN_REVIEW_DECISION=NOT_CREATED
TASK_ARCHIVAL=NOT_EXECUTED
MODEL_EXECUTION=NONE
```
