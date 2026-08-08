# ملف توريث شامل — المساعدون المحليون فقط
## PalWakf Local Agents | الحالة المعتمدة حتى 2026-06-27

> **نطاق هذا الملف:** مشروع المساعدين المحليين فقط. لا يمثل هذا الملف أي صلاحية أو حالة لمنصة PalWakf، أو Supabase، أو Flutter، أو قاعدة بيانات، أو Git، أو إنتاج.

---

## 1) بطاقة الاستئناف السريعة

```text
LOCAL_PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
CURRENT_PACKAGE_CLOSURE=LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_3_STATIC_VALIDATION_SCOPE_CLOSURE
PACK01_FINAL_CLOSURE_GATES=PASS
CORE_RUNTIME=FROZEN_FOR_READ_ONLY_PILOTS
EXECUTION_DEFAULT=disabled
PACK_RUNTIME_MODE=read_only_report_only
PACK_OPERATING_AUTONOMY=L0_READ_ONLY
HUMAN_REVIEW_REQUIRED=YES
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
```

### القرار التنفيذي
- تم إغلاق **Pack 01** بنجاح بعد تثبيت V1.2 وإغلاق نطاق التحقق الساكن عبر V1.3.
- لا يتم إعادة بناء أو تعديل `Evidence Gateway` أو `Runner` أو `Validator` أو عقد المخرجات V3 أثناء العمل على الأدوار الجديدة.
- لا توجد مهام Pilot منشأة تلقائيًا ضمن مرحلة الإغلاق؛ تقييمات Pack فقط هي التي نفذت.
- أي تشغيل جديد يجب أن يبقى مقيدًا بمهمة معتمدة، مراجع محلية معتمدة، ومراجعة بشرية.

---

## 2) الحالة المثبتة الأخيرة

### البوابات النهائية التي نجحت
```text
V1_3_PACKAGE_SYNTAX_GATE=PASS
V1_3_POST_INSTALL_PREFLIGHT=PASS
V1_3_STATIC_TEST=PASS
PACK01_TEMPLATE_PROFILE_EVALS=PASS_5_OF_5
PACK01_FINAL_CLOSURE_GATES=PASS
```

### تفاصيل الإغلاق
```text
REQUIRED_FILE_COUNT=20
MISSING_FILE_COUNT=0
REGISTRY_FAILURE_COUNT=0
PACK_OWNED_SCRIPT_COUNT=7
POWERSHELL_PARSE_FAILURE_COUNT=0
UNSAFE_VARIABLE_COLON_INTERPOLATION_COUNT=0
EVAL_CASE_COUNT=5
EVAL_PASSED_COUNT=5
EVAL_FAILED_COUNT=0
```

### حدود التنفيذ التي ثبتت أثناء الإغلاق
```text
MODEL_EXECUTION=NONE
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
```

> ملاحظة مهمة: سبق تشغيل Ollama بنجاح في Pilot الأساس الخاص بالـCore Runtime. أما إغلاق Pack 01 نفسه فلم ينفذ نموذجًا ولم ينشئ مهامًا.

---

## 3) بنية النظام المعتمدة

```text
User-approved task
        |
        v
Task / policy / reference eligibility checks
        |
        v
Read-only Evidence Gateway
        |
        v
Read-only runtime context construction
        |
        v
Local Ollama model (only when explicitly executed)
        |
        v
Strict 11-line model body validation
        |
        v
Host-generated canonical envelope
        |
        v
Raw output + canonical output + human review report
        |
        v
Human review only
```

### المبدأ الحاكم
النموذج لا يملك سلطة تشغيلية. دوره هو إرجاع جسم مضبوط. المضيف المحلي يتحقق من العقد وينشئ الغلاف القياسي. لا يتم قبول قرار أو تعلم أو ذاكرة أو إجراء تلقائيًا.

---

## 4) الـCore Runtime المجمد

### مصدر الحقيقة الفني
```text
runtime\ReadOnlyRuntimeContextEvidenceV1.psm1
scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1
scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1
task_contracts\MODEL_OUTPUT_CONTRACT_V1.json
reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md
```

### عقد المخرجات V3
النموذج يجب أن يعيد **11 سطرًا فقط** وبالترتيب المنصوص عليه:

```text
ROLE
TASK_STATUS
TASK_CLASS
TRUTH_SOURCE
LIVE_STATE_PROVEN
MUTATION_ALLOWED
EVIDENCE_STATUS
EVIDENCE_REFERENCE_IDS
UNCERTAINTY_STATUS
SECURITY_POSTURE
NEXT_STEP
```

### ملكية الغلاف
```text
MODEL_BODY=EXACTLY_11_KEY_VALUE_LINES
HOST_OWNS_START_BOUNDARY=OUTPUT_CONTRACT_START
HOST_OWNS_END_BOUNDARY=OUTPUT_CONTRACT_END
RAW_OUTPUT_ARTIFACT=REQUIRED
CANONICAL_OUTPUT_ARTIFACT=CREATED_ONLY_AFTER_VALIDATION
TRAILING_TEXT=REJECTED
EXTRA_MODEL_LINES=REJECTED
MODEL_GENERATED_BOUNDARIES=REJECTED
MODEL_GENERATED_TASK_ID=REJECTED
```

### Pilot أساسي ناجح سابق
تم إثبات تشغيل محلي مع `qwen2.5:3b` حيث:
```text
RUN_MODE=READ_ONLY_CONTEXT_EVIDENCE_MODEL_RUN
RUN_STATUS=PENDING_HUMAN_REVIEW
MODEL_EXECUTION=OLLAMA_LOCAL
MODEL_OUTPUT_VALID=True
MODEL_OUTPUT_RAW_LINE_COUNT=11
MODEL_OUTPUT_TRAILING_LINE_COUNT=0
SYSTEM_OWNED_ENVELOPE_CREATED=True
```

### قرار التغيير
```text
CORE_RUNTIME_CHANGE=ONLY_WITH_REPRODUCIBLE_FAILURE_AND_CONFIRMED_ROOT_CAUSE
```

---

## 5) Agent Registry — الحالة بعد Pack 01

### مصدر الحقيقة
```text
agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json
registry_version=1.0
execution_default=disabled
```

### Schema الفعلي لكائن Agent
```text
agent_id
allowed_autonomy
runtime_enabled
runtime_mode
allowed_skills
forbidden_capabilities
```

> لا تضف حقولًا جديدة إلى كائن Agent دون تعديل مستقل ومبرر للـRegistry schema.  
> `human_review_required` سياسة تشغيلية في المهمة/التقرير والحوكمة، وليست حقلًا مفترضًا داخل Registry.

### الأدوار الأربعة في Pack 01

| Agent | الحالة | Runtime Mode | سياق Pack 01 | ملاحظات |
|---|---:|---|---|---|
| `coordinator` | مفعّل | `read_only_report_only` | فرز المهمة وتقييم الأدلة | لديه قدرات إضافية موروثة، لكن تنفيذ Pack 01 يظل L0 فقط |
| `sovereignty_reviewer` | مفعّل | `read_only_report_only` | مراجعة الحوكمة والسيادة والحدود | أضيفت له `task_triage` للتوافق مع Pilots |
| `knowledge_researcher` | مفعّل بعد V1.2 | `read_only_report_only` | مراجعة المرجع المعتمد وحدود الثقة | كان `admission_required` قبل V1.2 |
| `documentation_handoff` | أضيف في V1.2 | `read_only_report_only` | أثر تسليم مقيد للمراجعة البشرية | دور جديد، وL0 فقط |

### دور خارج نطاق Pack 01
| Agent | الحالة المعروفة | ملاحظة |
|---|---|---|
| `ui_ux_designer` | بقي `admission_required` في آخر فحص قبل Pack 01 | لم يتغير ضمن Pack 01 ولا يجوز افتراض تفعيله |

### الاستقلالية
- التنفيذ التشغيلي المعتمد لـPack 01: `L0_READ_ONLY`.
- بعض الأدوار الموجودة مسبقًا تحمل `L1_PLAN_ONLY` في Registry كقدرة مسموحة سابقة، لكن ذلك **لا يمنحها تشغيلًا أو كتابة أو صلاحية أعلى داخل Pack 01**.
- `documentation_handoff` أضيف بـ `L0_READ_ONLY` فقط.

### محظورات الدور الجديد `documentation_handoff`
```text
sql_execute
git_write
file_modify_outside_output
deployment
secret_read
```

---

## 6) Pack 01 — نطاقه الحقيقي

### ما تمت إضافته
```text
agents\charters\read_only_analysis_pack_01\
agents\output_profiles\read_only_analysis_pack_01\
tasks\templates\read_only_analysis_pack_01\
governance\read_only_analysis_pack_01\
scripts\Test-ReadOnlyAnalysisPack01...
scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1
scripts\New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1
scripts\Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1
```

### الأدوار/المهارات المستعملة في هذه الدفعة
```text
task_triage
evidence_assessment
```

### نوع المهام
كل قوالب الـPilot الأربعة محددة كالآتي:
```text
RISK=LOW
AUTONOMY=L0_READ_ONLY
STATUS=PENDING_HUMAN_APPROVAL
ALLOWED_REFERENCE_PATHS=reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md
PROMPT_INJECTION_SUSPECTED=False
HUMAN_APPROVAL_REQUIRED=True
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
```

### ما لم تضفه Pack 01
- لا تحليل حر واسع من النموذج.
- لا Payload تحليلي منظم جديد.
- لا استيراد معرفة.
- لا تعديل وثائق تشغيلية تلقائيًا.
- لا بحث إنترنت.
- لا وصول إلى منصة PalWakf.
- لا قاعدة بيانات أو Supabase.
- لا Git أو Deployment.
- لا مهام تُعتمد أو تُشغّل تلقائيًا.

---

## 7) تسلسل الحزم والأدلة التاريخية

### المرحلة A — إغلاق Core Runtime
1. بناء أساس runtime مقيد بالقراءة.
2. إغلاق Evidence Gateway.
3. إغلاق تقديم تقرير Dry Run.
4. إصلاح عقد المخرجات عبر System-Owned Envelope.
5. اجتياز اختبارات ثابتة وحتمية.
6. نجاح Pilot فعلي لـ`coordinator` مع Ollama وCanonical Output.

### المرحلة B — Pack 01
| الإصدار | النتيجة | الدرس |
|---|---|---|
| Pack 01 V1.0 | لم يطبق؛ ParserError | لا تستخدم `$variable:` داخل نص مزدوج الاقتباس عندما يقصد متغير عادي |
| V1.1 Parse-Safety | اجتاز Syntax Gate لكنه توقف في Preflight | لا تفترض أن Agent موجود في Registry |
| V1.2 Registry Bootstrap | تم التثبيت الفعلي | أضاف `documentation_handoff` وفعّل `knowledge_researcher` |
| V1.2 Static Test | false positive | لا تفحص Scripts خارج ملكية الـPack |
| V1.3 Static Validation Scope Closure | تم التثبيت والقبول | تحقق من Pack-owned scripts فقط، واسمح PowerShell scopes الصحيحة |

### الدروس المحفوظة
1. **Syntax gate قبل أي WhatIf أو تطبيق.**
2. **Preflight يجب أن يطابق الحالة السابقة المتوقعة بدقة.**
3. **Bootstrap لا يطلب وجود ما يريد إنشاءه.**
4. **اختبارات الحزمة لا تفحص نطاقًا غير مملوك لها.**
5. **`$script:` و`$env:` PowerShell scopes صحيحة، وليست unsafe interpolation.**
6. **`$agentId:` داخل نص قد يسبب ParserError؛ استخدم `${agentId}:`.**
7. **لا تعتبر Echo يدويًا لنجاح العملية بديلًا عن `FINAL_RESULT=PASS` الفعلي.**

---

## 8) مسارات الأدلة والنسخ الاحتياطي

### Registry backup قبل V1.2
```text
C:\Users\DELL\StudioProjects\palwakf_local_agents\backups\read_only_analysis_pack_01_v1_2_20260627153253
```

### تقرير Pack 01 Evals الأخير
```text
C:\Users\DELL\StudioProjects\palwakf_local_agents\output\evals\READ_ONLY_ANALYSIS_PACK_01_V1_2_EVAL_REPORT_20260627160635.json
```

### مخرجات Core Runtime الموثقة سابقًا
```text
output\read_only_context_runs\
output\evidence_manifests\
runtime\context\
output\evals\
```

> لا تتعامل مع أي مسار سابق أو ملف تقييم على أنه دليل كافٍ وحده؛ أعد تشغيل بوابات القراءة في بداية أي جلسة استئناف.

---

## 9) بروتوكول الاستئناف الإلزامي

### قبل أي عمل جديد
1. اقرأ هذا الملف وملف Baseline المرافق.
2. تحقق من وجود المشروع في المسار الصحيح.
3. شغّل بوابات الحالة التالية فقط:

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
```

### القبول قبل الاستمرار
```text
PREFLIGHT_RESULT=PASS
FINAL_RESULT=PASS
EVAL_FAILED_COUNT=0
```

### عند فشل أي بوابة
- توقف.
- لا تشغّل Ollama.
- لا تنشئ مهام.
- لا تعدّل Registry.
- اجمع كامل الناتج مع اسم السكربت والمسار، ثم نفذ Root Cause محددًا.

---

## 10) إنشاء مهام Pilot لاحقًا

### ما هو مسموح
إنشاء قوالب Pack 01 فقط في `tasks\inbox`، وبعد طلب صريح. هذه المهام يجب أن تبقى:
```text
PENDING_HUMAN_APPROVAL
```

### ما هو غير مسموح دون فحص مستقل
- نقل مهمة من Inbox إلى Approved.
- تعديل محتوى المهمة بعد إنشائها.
- تشغيل مهمة غير معتمدة.
- تشغيل أكثر من Pilot واحد في الوقت نفسه.
- تشغيل Agent غير مدرج في Pack 01.
- منح وصول لمصدر خارج `reference_sources/approved`.

### ملاحظة تشغيلية
آلية اعتماد المهمة الموجودة في المشروع لم تُثبت هنا كجزء من Pack 01. لا تخترع مسار اعتماد أو تنفذ نقلًا يدويًا قبل فحص سياسة/سكريبت الاعتماد الفعليين.

---

## 11) شروط أي Model Run مستقبلي

لا يبدأ `-Execute` إلا إذا تحقق جميع ما يلي:
```text
TASK_EXISTS=YES
TASK_APPROVED=YES
AGENT_RUNTIME_ENABLED=YES
AGENT_RUNTIME_MODE=read_only_report_only
RISK=LOW
AUTONOMY=L0_READ_ONLY
ALLOWED_REFERENCE_PATHS=APPROVED_ONLY
HUMAN_REVIEW_REQUIRED=YES
PRECHECKS=PASS
```

وبعده يجب فحص:
```text
MODEL_OUTPUT_VALID=True
MODEL_OUTPUT_RAW_LINE_COUNT=11
MODEL_OUTPUT_TRAILING_LINE_COUNT=0
SYSTEM_OWNED_ENVELOPE_CREATED=True
RUN_STATUS=PENDING_HUMAN_REVIEW
```

لا تحول النتيجة إلى Memory أو قرار أو تنفيذ أو نشر تلقائيًا.

---

## 12) المسار التالي المقترح بعد Pack 01

### الأولوية التالية
```text
LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION
```

### الهدف
إضافة Payload تحليلي منظم وقابل للتحقق، **منفصل** عن Core Envelope الحالي، لكي تصبح أدوار مثل:
- `knowledge_researcher`
- `documentation_handoff`

قادرة على إنتاج مخرجات تخصصية مفيدة، دون التضحية بصرامة العقد الأساسي.

### شروط بناء الدفعة التالية
1. لا تعديل عقد الـ11 سطرًا الأساسي.
2. Schema مستقل للـPayload.
3. Validator مستقل.
4. Raw/Canonical separation.
5. قيود حجم ومحتوى واضحة.
6. Human review gate.
7. Deterministic evals خاصة بكل Role.
8. عدم إعادة فتح Platform/DB/Git/Deployment/Secrets.
9. Pilot واحد لكل Role بعد الإغلاق.

---

## 13) المخاطر المتبقية

| بند | الحالة | المعالجة |
|---|---|---|
| التحليل الغني للأدوار | غير مفعل عمدًا | Structured Analysis Payload لاحقًا |
| آلية اعتماد Task | ليست جزءًا من هذا الإغلاق | فحص منفصل قبل نقل أي Task |
| معرفة/مصادر حقيقية واسعة | غير مفعلة | تظل Approved Local References فقط |
| استمرارية الإغلاق | تحتاج re-check عند الاستئناف | شغل Preflight + Static + Evals |
| التوسع في الاستقلالية | غير مصرح | يبقى L0_READ_ONLY |
| التكامل مع المنصة | محظور | يبقى خارج مشروع local agents |

---

## 14) قرار الحالة النهائي

```text
LOCAL_AGENT_CORE_RUNTIME=ACCEPTED_FOR_READ_ONLY_PILOTS
LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01=ACCEPTED_AND_CLOSED
PACK01_FINAL_CLOSURE_GATES=PASS
REGISTRY_BOOTSTRAP=APPLIED
STATIC_VALIDATION_SCOPE=CORRECTED_AND_VERIFIED
NEXT_DEVELOPMENT=STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION
```

---

## 15) ملخص تنفيذي لبدء جلسة جديدة

```text
ابدأ من:
C:\Users\DELL\StudioProjects\palwakf_local_agents

الحالة:
Core runtime مجمد ومقبول للقراءة فقط.
Pack 01 مغلق: 4 أدوار مقيدة.
Registry محدث: documentation_handoff موجود، knowledge_researcher مفعّل للقراءة فقط.
لا تنفذ Ollama أو تولد Tasks أو تنقل مهام لاعتماد دون طلب صريح وبوابة تحقق.
لا تعدل core runtime إلا بفشل قابل لإعادة الإنتاج وسبب جذري مثبت.
الدفعة التالية المقترحة:
LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION
```
