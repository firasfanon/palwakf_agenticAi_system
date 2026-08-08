# Baseline محدث — المساعدون المحليون فقط
## PalWakf Local Agents | Accepted Baseline | 2026-06-27

> **حالة هذا الملف:** Baseline توثيقي مبني على مخرجات إغلاق فعلية. ليس بديلًا عن إعادة تشغيل بوابات التحقق عند بداية أي جلسة جديدة.

---

## 1) الهوية

```text
BASELINE_ID=PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_2026_06_27
PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
SCOPE=LOCAL_AGENTS_ONLY
EXECUTION_DEFAULT=disabled
CURRENT_CLOSURE=LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3_STATIC_VALIDATION_SCOPE_CLOSURE
BASELINE_STATUS=ACCEPTED_FOR_READ_ONLY_PILOTS
```

---

## 2) الحالة الحاكمة

```text
CORE_RUNTIME=FROZEN
CORE_RUNTIME_CHANGE=ONLY_WITH_REPRODUCIBLE_FAILURE_AND_CONFIRMED_ROOT_CAUSE
PACK01_STATUS=ACCEPTED_AND_CLOSED
PACK01_FINAL_CLOSURE_GATES=PASS
AUTONOMY=L0_READ_ONLY
RUNTIME_MODE=read_only_report_only
HUMAN_REVIEW_REQUIRED=YES
```

---

## 3) حدود عدم الصلاحية

```text
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
MODEL_EXECUTION=DISABLED_BY_DEFAULT
```

### تفسير
- لا يوجد اتصال تشغيلي بمنصة PalWakf ضمن هذه الـBaseline.
- لا توجد صلاحية Supabase أو SQL أو RLS أو ملفات Flutter.
- لا يوجد نشر أو Git write أو secret read.
- لا يتم كتابة Memory أو اعتماد نتائج تلقائيًا.
- التنفيذ المحلي للنموذج لا يتم إلا عبر `-Execute` بعد مهمة معتمدة وبوابات سابقة ناجحة.

---

## 4) Core Runtime Baseline

### الملفات الحاكمة
```text
runtime\ReadOnlyRuntimeContextEvidenceV1.psm1
scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1
scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1
task_contracts\MODEL_OUTPUT_CONTRACT_V1.json
reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md
```

### بروتوكول المخرجات
```text
MODEL_BODY_LINES=11_EXACTLY
HOST_GENERATES=OUTPUT_CONTRACT_START_AND_OUTPUT_CONTRACT_END
RAW_OUTPUT=RETAINED
CANONICAL_OUTPUT=ONLY_AFTER_VALIDATION
TRAILING_TEXT=REJECTED
```

### حالة Pilot الأساسي
```text
MODEL=qwen2.5:3b
MODEL_EXECUTION=OLLAMA_LOCAL
MODEL_OUTPUT_VALID=True
MODEL_OUTPUT_RAW_LINE_COUNT=11
MODEL_OUTPUT_TRAILING_LINE_COUNT=0
SYSTEM_OWNED_ENVELOPE_CREATED=True
RUN_STATUS=PENDING_HUMAN_REVIEW
```

---

## 5) Registry Baseline

### Metadata
```text
REGISTRY_FILE=agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json
REGISTRY_VERSION=1.0
EXECUTION_DEFAULT=disabled
```

### حالة الأدوار

| Agent | runtime_enabled | runtime_mode | Pack 01 state |
|---|---:|---|---|
| `coordinator` | `true` | `read_only_report_only` | مفعل |
| `sovereignty_reviewer` | `true` | `read_only_report_only` | مفعل |
| `knowledge_researcher` | `true` | `read_only_report_only` | تمت ترقيته من `admission_required` في V1.2 |
| `documentation_handoff` | `true` | `read_only_report_only` | أضيف في V1.2 |
| `ui_ux_designer` | غير داخل Pack 01 | غير داخل Pack 01 | بقي خارج نطاق هذه الـBaseline التشغيلية |

### Runtime roles المعتمدة
```text
coordinator
sovereignty_reviewer
knowledge_researcher
documentation_handoff
```

### Pack 01 skills المطلوبة
```text
task_triage
evidence_assessment
```

---

## 6) Pack 01 Artifacts

### Charters
```text
agents\charters\read_only_analysis_pack_01\
```

### Output profiles
```text
agents\output_profiles\read_only_analysis_pack_01\
```

### Pilot templates
```text
tasks\templates\read_only_analysis_pack_01\
```

### Governance
```text
governance\read_only_analysis_pack_01\
```

### Scripts الرئيسية
```text
scripts\Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1
scripts\Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1
scripts\Install-ReadOnlyAnalysisPack01V1_2.ps1
scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1
scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1
scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1
scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1
scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1
```

---

## 7) إثبات الإغلاق

```text
V1_3_PACKAGE_SYNTAX_GATE=PASS
V1_3_POST_INSTALL_PREFLIGHT=PASS
V1_3_STATIC_TEST=PASS
PACK_OWNED_SCRIPT_COUNT=7
POWERSHELL_PARSE_FAILURE_COUNT=0
UNSAFE_VARIABLE_COLON_INTERPOLATION_COUNT=0
PACK01_EVAL_CASE_COUNT=5
PACK01_EVAL_PASSED_COUNT=5
PACK01_EVAL_FAILED_COUNT=0
PACK01_FINAL_CLOSURE_GATES=PASS
```

### آخر تقرير Evals معروف
```text
output\evals\READ_ONLY_ANALYSIS_PACK_01_V1_2_EVAL_REPORT_20260627160635.json
```

### Registry Backup قبل Bootstrap
```text
backups\read_only_analysis_pack_01_v1_2_20260627153253
```

---

## 8) المشاكل المغلقة تاريخيًا

| معرف | الحالة | الإغلاق |
|---|---|---|
| MODEL OUTPUT boundary ownership | مغلق | Host-owned canonical envelope |
| Extra `TASK_ID` / boundary fields | مغلق | Strict 11-line model body |
| Missing start boundary from model | مغلق | Host creates envelope |
| Dry Run report formatting | مغلق | raw/canonical sections corrected |
| `$agentId:` parser error | مغلق | `${agentId}:` |
| Missing `documentation_handoff` in registry | مغلق | V1.2 schema-backed bootstrap |
| Global script false-positive scan | مغلق | V1.3 Pack-owned validation scope |

---

## 9) إعادة التحقق عند الاستئناف

```powershell
$target = "C:\Users\DELL\StudioProjects\palwakf_local_agents"

& "$target\scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1" `
  -ProjectRoot $target

if ($LASTEXITCODE -ne 0) {
  throw "PACK01_PRECHECK_FAILED"
}

& "$target\scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1" `
  -ProjectRoot $target

if ($LASTEXITCODE -ne 0) {
  throw "PACK01_STATIC_GATE_FAILED"
}

& "$target\scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1" `
  -ProjectRoot $target

if ($LASTEXITCODE -ne 0) {
  throw "PACK01_EVAL_GATE_FAILED"
}

"LOCAL_AGENTS_BASELINE_RECHECK=PASS"
```

### نتيجة مطلوبة
```text
PREFLIGHT_RESULT=PASS
FINAL_RESULT=PASS
EVAL_FAILED_COUNT=0
LOCAL_AGENTS_BASELINE_RECHECK=PASS
```

---

## 10) قواعد العمل التالية

```text
NO_UNAPPROVED_TASK_EXECUTION
NO_AUTO_APPROVAL
NO_AUTO_MEMORY_WRITE
NO_PLATFORM_SCOPE
NO_DB_SCOPE
NO_GIT_SCOPE
NO_DEPLOYMENT_SCOPE
NO_SECRETS_SCOPE
ONE_PILOT_AT_A_TIME
HUMAN_REVIEW_REQUIRED
```

---

## 11) الحالة القادمة

```text
NEXT_RECOMMENDED_MEGA_BATCH=LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION
```

### الغرض
تأسيس Payload منظم وقابل للتحقق للأدوار المتخصصة، دون تغيير Core Runtime أو عقد الـ11 سطرًا الأساسي.

### غير مسموح قبل هذه الدفعة
- ادعاء أن `knowledge_researcher` ينتج بحثًا معرفيًا غنيًا.
- ادعاء أن `documentation_handoff` يكتب تسليمات تحريرية مفصلة تلقائيًا.
- توسيع أي Agent إلى صلاحيات كتابة أو أدوات أو اتصالات خارجية.

---

## 12) Baseline acceptance statement

```text
LOCAL_AGENT_CORE_RUNTIME=ACCEPTED_FOR_READ_ONLY_PILOTS
LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01=ACCEPTED_AND_CLOSED
REGISTRY_BOOTSTRAP=APPLIED
STATIC_VALIDATION_SCOPE=CORRECTED_AND_VERIFIED
HUMAN_REVIEW=REQUIRED
```
