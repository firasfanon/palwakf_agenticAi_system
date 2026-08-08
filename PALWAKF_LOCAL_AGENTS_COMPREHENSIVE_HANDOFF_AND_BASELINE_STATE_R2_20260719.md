# ملف التوريث الشامل جدًا وخط حالة الأساس المحدث — بعد قبول مزود النموذج
## مشروع PalWakf Local Agents — منصة المساعدين المحليين الهندسية المحكومة

**اسم حزمة التوريث:**  
`PALWAKF_LOCAL_AGENTS_COMPREHENSIVE_HANDOFF_AND_UPDATED_BASELINE_STATE_R2_20260719`

**تاريخ الحالة:** 2026-07-19  
**لغة التشغيل والواجهات:** العربية أولًا، RTL  
**مسار المشروع المحلي المعتمد:**  
`C:\Users\DELL\StudioProjects\palwakf_local_agents`

**جذر الأدلة وخطوط الأساس:**  
`D:\PALWAKF_ASSISTANT_BASELINES`

**عنوان التشغيل المحلي المتوقع:**  
`http://127.0.0.1:8010/agent-console/`

---

# 0. تنبيه مهم حول معنى هذا الملف

هذه الحزمة هي **خط حالة أساس توثيقي وتشغيلي شامل** للتوريث بين الجلسات. وهي تتضمن:

- الحالة الحاكمة الدقيقة للمشروع.
- خطوط الأساس المقبولة.
- الحزم والأدلة المعروفة.
- الحدود الأمنية والتشغيلية.
- حالة الأدوات والمساعدين والـCandidates.
- خطة المراحل التالية.
- تعليمات استئناف الجلسة الجديدة.
- سكربت PowerShell لإنشاء Snapshot فعلي من المصدر المحلي على جهاز Windows.

هذه الحزمة **ليست نسخة من Source المشروع نفسه**؛ لأن المصدر الفعلي موجود على جهاز Windows خارج بيئة هذه الجلسة. لذلك أُرفق سكربت مستقل لإنشاء Source Baseline محلي فعلي بعد تشغيله من الجهاز، دون تعديل المصدر.

---

# 1. الملخص التنفيذي

وصل المشروع إلى نقطة انتقال مهمة: لم يعد مجرد واجهة أو قارئ مشروع، بل أصبح يملك سلسلة تطوير برمجي محكومة تشمل:

```text
Goal
→ Project Understanding
→ Tool Quality Gate
→ Human Authorization
→ Read-Only Operations
→ Evidence Capture
→ Candidate Workspace
→ Controlled File Editing
→ Direct-Argv Tests
→ Unified Diff
→ Human Review
→ Source Apply Still Blocked
```

أحدث خط أساس **مقبول رسميًا** هو:

```text
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
```

وقد سُجل القبول الصريح من المستخدم بتاريخ 2026-07-19 بعد نجاح:

```text
TECHNICAL_RESULT=PASS
VISUAL_UAT=PASS
ACCESSIBILITY_UI=PASS
VISUAL_CONTRAST_REPAIR=PASS
```

الحالة الحاكمة بعد القبول:

```text
FORMAL_ACCEPTED_BASELINE=
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719

ACCEPTANCE_TOKEN_RECORDED=YES
MODEL_LIVE_CALL=NOT_YET_PERFORMED
MODEL_EXECUTION=REQUIRES_SEPARATE_EXPLICIT_HUMAN_AUTHORIZATION
SOURCE_APPLY=BLOCKED
NETWORK_SCOPE=LOOPBACK_ONLY
SHELL=BLOCKED
GIT=BLOCKED
DATABASE_WRITE=NONE
SELF_APPLY=BLOCKED
```

هذا القبول يثبت واجهة مزود النموذج وعقوده وحدوده، ولا يُعد تفويضًا لتشغيل نموذج حي أو تطبيق Candidate على المصدر.

---

# 1.1 سجل القبول الجديد

```text
EVENT=FORMAL_BASELINE_ACCEPTANCE
PHASE=GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1
TOKEN=GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
RECORDED_DATE=2026-07-19
PREVIOUS_FORMAL_BASELINE=CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_V1_0_1_ACCEPTED_20260719
NEW_FORMAL_BASELINE=GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
```

## ما تم قبوله

- واجهة إعداد مزود النموذج البرمجي المحكوم.
- أوضاع `disabled` و`ollama` و`openai_compatible`.
- قيد Loopback ومنع Redirects وProxy.
- عدم تخزين أو إرجاع قيمة مفتاح API.
- مسار إنشاء Candidate داخل Workspace معزول.
- الإصلاح البصري وإمكانية الوصول المثبتة بالـUAT.

## ما لم يتم تفويضه

- أي استدعاء حي لنموذج.
- أي اتصال خارج Loopback.
- أي Shell أو Git.
- أي Database Write.
- أي تطبيق Candidate على Source الحقيقي.
- أي Self-Apply أو تشغيل إنتاجي.

---

# 2. هوية المشروع والغرض منه

## 2.1 الاسم الرسمي

```text
PalWakf Local Agents
Governed Local Engineering Agentic Platform
```

## 2.2 الغرض

بناء منظومة مساعدين محليين قادرة على:

- فهم مشاريع البرمجيات المحلية.
- تحويل الأهداف إلى خطط ومهام.
- اختيار الأدوات المقبولة جودة.
- تنفيذ عمليات قراءة فقط محكومة.
- إنتاج أدلة وتقارير قابلة للتدقيق.
- إنشاء تعديلات برمجية داخل Workspace معزول.
- اختبار الـCandidate قبل أي تطبيق.
- عرض Unified Diff والاختبارات والمخاطر.
- إبقاء القرار النهائي والتطبيق تحت سلطة بشرية صريحة.
- دعم مزود نموذج برمجي محلي أو OpenAI-compatible محلي عبر Loopback فقط.
- التطور لاحقًا نحو RAG، ذاكرة طبقية، Skill Registry، فريق متعدد المساعدين، MCP محكوم، وقواعد بيانات مصنفة الصلاحيات.

## 2.3 المبادئ الحاكمة

```text
HUMAN_AUTHORITY
GOAL_TO_PLAN_FIRST
TOOL_CONTRACTS
QUALITY_BEFORE_SELECTION
LOCAL_SOVEREIGNTY
PRIVACY_BY_DEFAULT
NO_HIDDEN_EXECUTION
NO_SELF_APPLY
NO_AUTONOMOUS_SOURCE_WRITE
EVIDENCE_BEFORE_ACCEPTANCE
FAIL_CLOSED
```

---

# 3. بيئة التشغيل ومسارات العمل

## 3.1 البيئة المعروفة

```text
OS=Windows
POWERSHELL=5.1
NODE=24.16.0
PNPM=via corepack
FLUTTER=3.44.1
DART=3.12.1
PYTHON_VENV=<project>\.venv
```

## 3.2 المسارات

```text
SOURCE_ROOT=
C:\Users\DELL\StudioProjects\palwakf_local_agents

BASELINE_ROOT=
D:\PALWAKF_ASSISTANT_BASELINES

PYTHON=
C:\Users\DELL\StudioProjects\palwakf_local_agents\.venv\Scripts\python.exe

RUNTIME=
127.0.0.1:8010
```

## 3.3 قواعد PowerShell

- استخدام `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`.
- استخدام `npm.cmd` بدل `npm`.
- تشغيل أوامر الحزم داخل ScriptBlock واحد Fail-Fast عند الإمكان.
- عدم طباعة `FINAL_RESULT=PASS` يدويًا.
- عدم الاستمرار بعد `ZIP_NOT_FOUND` أو Hash mismatch.
- إعادة تعيين المتغيرات داخل النطاق لتجنب بقايا `$item` و`$actualHash`.
- فحص الأحرف غير القانونية داخل Runner.
- لا يُعد أي نص مطبوع يدويًا دليلًا؛ الدليل هو نتيجة Runner فقط.

---

# 4. سجل خطوط الأساس المقبولة

## 4.1 مرجع UI/UX

```text
LOCAL_AGENTS_PROJECT_UI_UX_REFERENCE_SCREENS_V1_ACCEPTED_20260712
```

قواعده:

- العربية RTL.
- هوية داكنة.
- Operational UX First.
- إظهار Local Only والحدود.
- عدم إظهار تنفيذ فعلي بلا Backend Contract.
- استخدام حالات:
  - `READ_ONLY`
  - `BLOCKED`
  - `READINESS_HOLD`
  - `REVIEW_REQUIRED`

## 4.2 Open Source Capability Census

```text
OPEN_SOURCE_CAPABILITY_CENSUS_AND_SAFE_ADAPTER_CONTRACTS_V1_READ_ONLY_ACCEPTED
```

المعنى:

- جرد الأدوات وقدراتها.
- عقود Adapter آمنة.
- عدم اعتبار اكتشاف الأداة قبولًا تشغيليًا.
- الأدوات تمر عبر Admission وBenchmark وBaseline.

## 4.3 ربط Planner بالأدوات المقبولة جودة

```text
QUALITY_ACCEPTED_TOOLS_GOAL_PLANNER_SELECTION_BINDING_V1_ACCEPTED_20260713
```

دليل إصلاح FastAPI النهائي:

```text
PACKAGE=
LOCAL_AGENTS_QUALITY_PLANNER_EXACT_FACTORY_REPAIR_AND_OPENAPI_HTTP_VERIFICATION_V5_1_BUILT_APPLY_PACKAGE_20260713.zip

SHA256=
85DA7F072526D1E881ADF468156498204E767CE73F5269CB1BC08F84762EEE70
```

المبدأ المهم:

- FastAPI قد يحفظ APIRouter ضمن تركيب داخلي لا يظهر في فحص `app.routes` السطحي.
- التحقق الصحيح يعتمد:
  - OpenAPI paths.
  - In-process ASGI HTTP.
  - استيراد التطبيق الحقيقي.

## 4.4 مصالحة حالة جودة الأدوات

```text
TOOL_QUALITY_STATE_RECONCILIATION_AND_FIRST_SELECTABLE_TOOL_ACTIVATION_V1_ACCEPTED_20260713
```

الحالة المرجعية:

```text
TOOLS_MONITORED=8
SELECTABLE=1
BLOCKED_OR_FORBIDDEN=7
```

الأداة المقبولة:

```text
TOOL_ID=native-code-index
QUALITY_STATE=QUALITY_ACCEPTED
PLANNER_STATE=SELECTABLE
SCORE=100/100
BASELINE=PRESENT
SUITE=native_code_index_contract_v1
```

## 4.5 أول عملية بشرية مقروءة فقط

```text
FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_V1_ACCEPTED_20260713
```

الحزمة:

```text
LOCAL_AGENTS_FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_V1_BUILT_APPLY_PACKAGE_20260713.zip
SHA256=C4ED9546DDC850ABE52EE8A4E9CFC190BAB5A9B9893BDA6514558FC82037988D
```

الدليل:

```text
D:\PALWAKF_ASSISTANT_BASELINES\
LOCAL_AGENTS_FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_V1_20260713_025738
```

العملية:

```text
READ_ONLY_CODEBASE_INDEX_AND_STRUCTURE_REPORT
```

الحدود المثبتة:

```text
SOURCE_MUTATION_DURING_OPERATION=FALSE
MODEL_EXECUTION=NONE
DATABASE_WRITE=NONE
SHELL_GIT_NETWORK=BLOCKED
HUMAN_AUTHORITY=CONFIRMED
```

واجهة العملية:

```text
/agent-console/first-read-only-operation
```

## 4.6 خط تطوير البرمجيات المحكوم

```text
CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_V1_0_1_ACCEPTED_20260719
```

الحزمة المصححة:

```text
LOCAL_AGENTS_CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_AND_FIRST_CANDIDATE_PATCH_V1_0_1_BUILT_APPLY_PACKAGE_20260716.zip

SHA256=
A304784BC973875498BE5493004C101B116B8AED2D19B17CC926C6C76E62707A
```

الدليل:

```text
D:\PALWAKF_ASSISTANT_BASELINES\
LOCAL_AGENTS_CONTROLLED_SOFTWARE_DEVELOPMENT_PIPELINE_AND_FIRST_CANDIDATE_PATCH_V1_0_1_20260719_120130
```

النتيجة:

```text
PACKAGE_SELFTEST=PASS
APPLY=PASS
SOURCE_MUTATION_COUNT=0
VERIFY_RESULT=PASS
STATIC_GATE_REPAIR=PASS
IDEMPOTENCY_SECOND_APPLY=PASS
FINAL_RESULT=PASS
```

الواجهة:

```text
/agent-console/development-pipeline
```

---

# 5. حالة الحزم المبنية والقبول النهائي

## 5.1 Evidence Workbench

الحزمة:

```text
LOCAL_AGENTS_READ_ONLY_OPERATION_EXPANSION_AND_EVIDENCE_WORKBENCH_V1_BUILT_APPLY_PACKAGE_20260713.zip

SHA256=
0E5A052FB4201B5CAB097C6587807D77A3549318C362716B0A11CB09A36E2481
```

Updates-only:

```text
SHA256=
27AF09597904BF4AA60DEAF339384AD5EAA505F821E566EFE234AF26A77D09CD
```

الحالة الدقيقة:

```text
PACKAGE_BUILT=YES
INTERNAL_VALIDATION=PASS
WINDOWS_APPLY_EVIDENCE=NOT_CAPTURED_IN_VISIBLE_SESSION
FINAL_ACCEPTANCE=NOT_RECORDED
```

لا يجوز افتراض تطبيقها أو قبولها دون دليل.

## 5.2 مزود النموذج البرمجي المحكوم — مقبول رسميًا

الحزمة:

```text
LOCAL_AGENTS_GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_BUILT_APPLY_PACKAGE_20260719.zip

SIZE_BYTES=90996
SHA256=
B6ED2DC66BDD751148969B2886D54048E8754C607B59801C29C2F75572ABA76F
```

Updates-only:

```text
SIZE_BYTES=53072
SHA256=
49534C19169EFCE01FE3D9F51B17CA206A0E1B56580710BC739AF35CDF939539
```

الحالة:

```text
RUNTIME_PAGE_VISIBLE=YES
BACKEND_CONTRACT_VISIBLE=YES
VISUAL_UAT_AFTER_REPAIR=PASS
EXPLICIT_FINAL_ACCEPTANCE=RECORDED
ACCEPTED_BASELINE=GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
MODEL_LIVE_CALL=NOT_EXECUTED
PROVIDER_CURRENT_MODE=disabled
SOURCE_APPLY=BLOCKED
```

## 5.3 إصلاح التباين والوصولية

الحزمة:

```text
LOCAL_AGENTS_GOVERNED_CODING_MODEL_PROVIDER_VISUAL_CONTRAST_AND_ACCESSIBILITY_REPAIR_V1_BUILT_APPLY_PACKAGE_20260719.zip

SIZE_BYTES=16003
SHA256=
6C35DE09E779479A415AD4E2E2FE80DDB04BB0834215DABD02D0A88A97B191FB
```

Updates-only:

```text
SIZE_BYTES=3612
SHA256=
BDE232EF57846BC0D426B81B1A4293F0CDE38A0F1E5A6C3E5BE9229F1E1CB602
```

الدليل:

```text
D:\PALWAKF_ASSISTANT_BASELINES\
LOCAL_AGENTS_GOVERNED_CODING_MODEL_PROVIDER_VISUAL_CONTRAST_AND_ACCESSIBILITY_REPAIR_V1_20260719_132304
```

نتائج الإصلاح:

```text
SOURCE_MUTATION_COUNT=1
SOURCE_SCOPE=CSS_ONLY
BACKEND_MUTATION=NONE
JAVASCRIPT_MUTATION=NONE
MODEL_EXECUTION=NONE
SOURCE_APPLY_CAPABILITY_CHANGE=NONE
VERIFY_RESULT=PASS
ACCESSIBILITY_CONTRAST_GATE=PASS
FINAL_RESULT=PASS
```

نسب التباين:

```text
HEADING_BODY=17.25
HEADING_CARD=16.02
SECONDARY_BODY=12.62
FORM_LABEL_CARD=12.92
PLACEHOLDER_INPUT=8.98
FOCUS_BODY=11.38
```

Visual UAT:

```text
VISUAL_UAT=PASS
VISUAL_CONTRAST_REPAIR=PASS
ACCESSIBILITY_UI=PASS
```

رمز القبول المسجل للمرحلة الكاملة:

```text
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
```

---

# 6. الـCandidate البرمجي المرجعي الحالي

```text
CANDIDATE_ID=cand-a1836fd428779f8a
STATE=HUMAN_REVIEW_REQUIRED
TESTS=PASS
SOURCE_MUTATION=FALSE
SOURCE_APPLY=BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION
```

الغرض:

```text
READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1
```

الملفات المقترحة:

```text
backend/src/palwakf_local_agents/development_diagnostic_v1.py
backend/src/palwakf_local_agents/app.py
```

المسار المقترح:

```text
GET /api/v1/operational-core/development-diagnostic/health
```

ما تم إثباته:

- Candidate Workspace معزول.
- تعديل النسخة المرشحة فقط.
- Unified Diff ظاهر.
- اختبارات Candidate ناجحة.
- المصدر الحقيقي لم يتغير.
- لا يوجد Apply endpoint.
- لا يوجد زر تطبيق على المصدر.
- يوجد اعتماد Candidate دون تطبيق.
- التطبيق يحتاج تفويضًا مستقلًا خاصًا بالـCandidate.

لا يجوز اعتباره مطبقًا أو مقبولًا على المصدر.

---

# 7. مزود النموذج البرمجي الحالي

## 7.1 واجهة التشغيل

```text
http://127.0.0.1:8010/agent-console/coding-model
```

## 7.2 أوضاع المزود

```text
disabled
ollama
openai_compatible
```

## 7.3 الحالة المرئية الأخيرة

```text
PROVIDER=disabled
MODEL_EXECUTION=DISABLED
QUALITY=QUALITY_ACCEPTED
PLANNER=SELECTABLE
NETWORK=LOOPBACK_ONLY
SOURCE_APPLY=BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION
```

الإعدادات الظاهرة:

```text
BASE_URL=http://127.0.0.1:11434
MODEL_NAME=qwen3-coder:latest
TIMEOUT_SECONDS=90
MAX_OUTPUT≈1800
TEMPERATURE≈0.1
API_KEY_ENV_NAME=PALWAKF_LOCAL_AGENTS_MODEL_API_KEY
```

تنبيه:

- ظهور هذه القيم في الواجهة لا يعني أن المزود مفعل.
- المزود الحالي `disabled`.
- لم يحدث Live Model Call.
- قيمة API Key نفسها لا تُخزن ولا تُعرض.
- يُخزن فقط اسم متغير البيئة.
- الاتصالات الخارجية محجوبة؛ Loopback فقط.
- Proxy وRedirects محجوبة.

## 7.4 API

```text
GET  /api/v1/operational-core/coding-model/health
GET  /api/v1/operational-core/coding-model/contract
GET  /api/v1/operational-core/coding-model/providers
GET  /api/v1/operational-core/coding-model/settings
POST /api/v1/operational-core/coding-model/settings
POST /api/v1/operational-core/coding-model/providers/probe
GET  /api/v1/operational-core/coding-model/runs
GET  /api/v1/operational-core/coding-model/runs/latest
GET  /api/v1/operational-core/coding-model/candidates
GET  /api/v1/operational-core/coding-model/candidates/latest
GET  /api/v1/operational-core/coding-model/candidates/{candidate_id}
POST /api/v1/operational-core/coding-model/candidates/generate
```

لا توجد Source Apply API.

---

# 8. الحدود الأمنية والتشغيلية الحالية

```text
PRODUCTION_EXECUTION=NOT_AUTHORIZED
MODEL_EXECUTION=EXPLICIT_HUMAN_AUTHORIZATION_ONLY
AUTOMATIC_MODEL_EXECUTION_DURING_APPLY=NONE
REAL_SOURCE_WRITE_BY_MODEL_CANDIDATE=NONE
CANDIDATE_WORKSPACE_WRITE=LOCAL_ONLY
AUTONOMOUS_SOURCE_WRITE=BLOCKED
AUTONOMOUS_APPLY=BLOCKED
SOURCE_APPLY_ENDPOINT=ABSENT
SHELL=BLOCKED
GIT=BLOCKED
NETWORK=LOOPBACK_ONLY_FOR_APPROVED_PROVIDER
DATABASE_WRITE=NONE
SELF_APPLY=BLOCKED
HUMAN_AUTHORITY=RETAINED
```

## 8.1 ملاحظات تقنية يجب عدم تجاوزها

- Direct-Argv Broker ليس Shell عامًا.
- Timeout في `subprocess.run` لا يثبت قتل كامل Child Process Tree.
- لا تدّعِ OS-level network isolation ما لم توجد آلية فعلية.
- لا تدّعِ Filesystem read-only فعليًا دون Enforcement.
- لا تعتبر MCP آمنًا تلقائيًا.
- لا تعتبر Tool مكتشفة = Tool مقبولة.
- لا تعتبر Candidate ناجح الاختبار = مسموح التطبيق.
- لا تعتبر Visual UAT = Acceptance ما لم يسجل المستخدم رمز القبول.

---

# 9. معمارية النظام المستهدفة

```text
User Goal
   ↓
Goal Planner
   ↓
Context Builder
   ├── Project Reader
   ├── Symbol / Route / Dependency Retrieval
   ├── Accepted Baselines
   ├── Project Decisions
   └── Task Memory
   ↓
Coordinator / State Machine
   ├── Architect Agent
   ├── Coding Agent
   ├── Test Agent
   ├── Security Reviewer
   ├── Sovereignty Reviewer
   └── Evidence Agent
   ↓
Skill Registry
   ↓
Governed Tool / MCP Gateway
   ↓
Candidate Workspace
   ↓
Direct-Argv Build and Test
   ↓
Unified Diff and Evidence
   ↓
Human Review
   ↓
Candidate-Specific Apply Authorization
   ↓
Backup / Apply / Verify / Rollback
   ↓
Accepted Baseline
```

## 9.1 المبدأ التنظيمي

```text
LIMITED_NUMBER_OF_AGENTS
+
COMPOSABLE_SKILL_REGISTRY
```

لا يُنشأ Agent مستقل لكل عملية صغيرة.

## 9.2 الذاكرة المستقبلية

```text
SESSION_MEMORY
PROJECT_MEMORY
OPERATIONAL_MEMORY
GOVERNANCE_MEMORY
CANDIDATE_MEMORY
LONG_TERM_KNOWLEDGE
```

## 9.3 الاسترجاع

البداية:

```text
EXACT_PATH_SEARCH
METADATA_SEARCH
KEYWORD_SEARCH
SYMBOL_INDEX
ROUTE_INDEX
DEPENDENCY_INDEX
```

ثم لاحقًا فقط:

```text
EMBEDDINGS
VECTOR_SEARCH
RERANKING
```

بعد Benchmark وقياس الحاجة.

## 9.4 RAG وContext Cache

```text
RAG=
المحتوى المتغير: Source, Diffs, Tests, Docs, Runs, Candidates

CONTEXT_CACHE=
المحتوى المستقر: Charter, Policies, Accepted Baselines, Tool Rules, Schemas
```

إبطال Cache عند تغير:

```text
BASELINE
TOOL_POLICY
PROJECT_HASH
SCHEMA_VERSION
GOVERNANCE_RULES
```

---

# 10. سياسة SQL المستقبلية

## DQL

```text
SELECT
DEFAULT=READ_ONLY_BY_CONTRACT
```

الضوابط:

- Schema allowlist.
- Row limit.
- Timeout.
- Query hash.
- Secret masking.
- No unbounded query.

## DML

```text
INSERT
UPDATE
DELETE
MERGE
DEFAULT=BLOCKED
```

الدورة:

```text
Preview
→ Human Authorization
→ Transaction
→ Row Scope
→ Execute
→ Verify
→ Commit or Rollback
```

## DDL

```text
CREATE
ALTER
DROP
TRUNCATE
```

لا تنفذ مباشرة:

```text
Migration Candidate
→ Static Validation
→ Review
→ Backup
→ Explicit Authorization
→ Controlled Migration
```

## DCL

```text
GRANT
REVOKE
ADMIN_ONLY
```

---

# 11. خطة المراحل التالية بحسب آخر التحديثات

## المرحلة 0 — القبول الرسمي لمزود النموذج — مكتملة

الحالة:

```text
STATUS=ACCEPTED
ACCEPTANCE_TOKEN=GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
RECORDED_ON=2026-07-19
```

بوابات القبول المثبتة:

```text
VISUAL_UAT=PASS
ACCESSIBILITY_UI=PASS
SOURCE_APPLY=BLOCKED
MODEL_EXECUTION=DISABLED_AT_ACCEPTANCE
NO_SECRET_EXPOSURE=PASS
```

القبول لا يفتح تشغيل النموذج تلقائيًا؛ أي Probe حي يحتاج تفويضًا منفصلًا.

---

## المرحلة 1 — أول تشغيل حي محكوم للنموذج

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_FIRST_GOVERNED_CODING_MODEL_PROBE_AND_MODEL_GENERATED_CANDIDATE_UAT_V1
```

الأهداف:

- تفعيل `ollama` أو `openai_compatible` محلي Loopback فقط.
- Probe آمن.
- تفويض تشغيل بشري صريح.
- Prompt محدود.
- Structured JSON.
- AST Safety Gate.
- Candidate Workspace فقط.
- Direct-Argv tests.
- Source integrity.
- لا Apply.

بوابات القبول:

```text
PROVIDER_PROBE=PASS
LOOPBACK_ONLY=PASS
REDIRECTS=BLOCKED
PROXY=DISABLED
SECRET_VALUE_NOT_STORED=PASS
MODEL_RUN_HUMAN_AUTHORIZED=PASS
STRUCTURED_OUTPUT=PASS
AST_SAFETY_GATE=PASS
CANDIDATE_TESTS=PASS
REAL_SOURCE_MUTATION=FALSE
SOURCE_APPLY=BLOCKED
```

---

## المرحلة 2 — استرجاع معرفة المشروع والذاكرة الطبقية

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_PROJECT_KNOWLEDGE_RETRIEVAL_AND_LAYERED_MEMORY_V1
```

النطاق:

- Symbol Retrieval.
- Route Retrieval.
- Dependency Retrieval.
- Documentation Retrieval.
- Accepted Baseline Context.
- Task Session Memory.
- Project Decision Memory.
- Candidate History.
- Provenance.
- Correction/expiry policy.
- Local-only storage.
- No vector DB في البداية.

البوابات:

```text
PROVENANCE_PRESENT=PASS
EXACT_RETRIEVAL=PASS
STALE_CONTEXT_REJECTED=PASS
NO_UNAPPROVED_MEMORY_WRITE=PASS
HUMAN_APPROVED_PERSISTENCE=PASS
```

---

## المرحلة 3 — Skill Registry والفريق الهندسي

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_SKILL_REGISTRY_AND_MULTI_AGENT_ENGINEERING_TEAM_V1
```

المساعدون:

- Coordinator.
- Architect.
- Coding.
- Testing.
- Security.
- Sovereignty.
- Review.
- Evidence.

المهارات:

- FastAPI.
- React.
- Flutter.
- SQL Migration Planning.
- Test Writing.
- Dependency Audit.
- Documentation.
- UI/UX Review.
- Release Evidence.

المبدأ:

```text
STATE_MACHINE_ORCHESTRATION
NOT_FREE_FORM_AGENT_CHAT
```

---

## المرحلة 4 — طبقة MCP محلية محكومة

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_GOVERNED_LOCAL_MCP_ADAPTER_LAYER_V1
```

الأدوات الأولى:

```text
project.read_structure
project.list_routes
project.find_symbols
evidence.list_runs
evidence.read_summary
```

الممنوع:

```text
shell.execute
git.push
database.write
filesystem.write_source
network.fetch_arbitrary
```

دورة قبول MCP:

```text
Discovery
→ Admission
→ Static Inspection
→ Capability Contract
→ Benchmark
→ Human Approval
→ Runtime Allowlist
```

---

## المرحلة 5 — Apply Broker محكوم للـCandidates

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_CANDIDATE_SPECIFIC_CONTROLLED_APPLY_BACKUP_VERIFY_AND_ROLLBACK_BROKER_V1
```

هذه المرحلة هي التي تكمل دورة التطوير فعليًا.

الدورة:

```text
Candidate Review
→ Candidate-Specific Authorization
→ Preimage Hash Gate
→ Backup
→ Exact Target Scope
→ Apply
→ Compile
→ Tests
→ Source Drift Check
→ Postimage Evidence
→ Accept or Rollback
```

شروطها:

- لا Apply عامًا.
- لا Token يعاد استخدامه.
- لا تعديل خارج Target list.
- Rollback تلقائي عند الفشل.
- قبول Baseline مستقل.

---

## المرحلة 6 — سياسة قواعد البيانات

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_GOVERNED_DATABASE_ACCESS_AND_SQL_CLASS_POLICY_V1
```

تشمل:

- DQL/DML/DDL/DCL classification.
- Read-only account.
- Query preview.
- Row and schema scope.
- Transaction.
- Commit/rollback.
- Migration candidates.
- DCL admin-only.

---

## المرحلة 7 — التقييم والمراقبة والإنتاجية

اسم مقترح:

```text
MEGA_BATCH_LOCAL_AGENTS_EVALUATION_OBSERVABILITY_AND_OPERATIONAL_RELIABILITY_V1
```

النطاق:

- Prompt/version logging.
- Token/time/resource metrics.
- Candidate quality metrics.
- Failure taxonomy.
- Tool/model benchmark history.
- Evidence completeness.
- Recovery and retention.
- No production authorization yet.

---

# 12. نقطة الاستئناف الموصى بها للجلسة الجديدة

```text
CURRENT_FORMAL_BASELINE=
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719

LATEST_TECHNICAL_STATE=
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1
WITH_VISUAL_REPAIR_PASS_AND_EXPLICIT_ACCEPTANCE

IMMEDIATE_DECISION=
DEFINE_AND_AUTHORIZE_FIRST_GOVERNED_MODEL_PROBE

NEXT_TASK=
MEGA_BATCH_LOCAL_AGENTS_FIRST_GOVERNED_CODING_MODEL_PROBE_AND_MODEL_GENERATED_CANDIDATE_UAT_V1
```

## القرار التالي المطلوب

يجب فصل قرارين بوضوح:

1. تفويض بناء/تطبيق مكونات الدفعة التالية على المصدر المحلي.
2. تفويض تشغيل Probe حي للنموذج عبر Loopback.

لا يُستنتج أي منهما من قبول المرحلة السابقة، ولا يجوز تنفيذ Live Model Call قبل تفويض بشري صريح.

---

# 13. سجل الأدلة والحزم

| المرحلة | الحزمة / الدليل | SHA-256 أو المسار | الحالة |
|---|---|---|---|
| Quality Planner V5.1 | Built Apply | `85DA7F...70` | Accepted predecessor |
| First Read-Only Operation | Built Apply | `C4ED9546...988D` | Accepted |
| First Read-Only Operation | Evidence Root | `...\20260713_025738` | PASS |
| Evidence Workbench | Built Apply | `0E5A052F...2481` | Built; apply unknown |
| Controlled Pipeline V1 | Built Apply | `4AA4557E...FEA6` | Static verify false positive |
| Controlled Pipeline V1.0.1 | Built Apply | `A304784B...07A` | Accepted |
| Controlled Pipeline V1.0.1 | Evidence Root | `...\20260719_120130` | PASS |
| Coding Model Provider V1 | Built Apply | `B6ED2DC6...76F` | Runtime present; acceptance pending |
| Visual Repair V1 | Built Apply | `6C35DE09...91FB` | Applied |
| Visual Repair V1 | Evidence Root | `...\20260719_132304` | PASS |

---

# 14. الأخطاء السابقة والدروس المستفادة

## 14.1 FastAPI route verification

لا تعتمد على `app.routes` فقط. استخدم:

- OpenAPI.
- ASGI in-process HTTP.
- التطبيق الفعلي.

## 14.2 Static gate false positive

الفحص النصي لعبارة:

```text
تطبيق على المصدر
```

التقط رسالة النفي:

```text
لا يوجد زر تطبيق على المصدر
```

الإصلاح الصحيح:

- فحص بنيوي للأزرار.
- فحص `data-decision`.
- فحص fetch endpoints.
- إثبات غياب Apply API.

## 14.3 ZIP_NOT_FOUND وسياق PowerShell

عند فشل ZIP_NOT_FOUND، بقيت متغيرات قديمة من حزمة سابقة، فظهرت قيم حجم وHash غير صحيحة.

القاعدة الجديدة:

```text
ONE_SCRIPTBLOCK
STRICT_MODE
FAIL_FAST
FRESH_VARIABLES
NO_MANUAL_PASS_PRINTING
```

---

# 15. قائمة عدم الافتراض في الجلسة الجديدة

لا تفترض:

- أن Evidence Workbench طُبق.
- أن Coding Model Provider مقبول رسميًا.
- أن Live Model Call حدث.
- أن Candidate `cand-a1836fd428779f8a` طُبق.
- أن Source Apply مسموح.
- أن Model Network خارجي مسموح.
- أن API Key مخزن.
- أن MCP آمن تلقائيًا.
- أن قاعدة بيانات مسموح تعديلها.
- أن Production مصرح.
- أن Git أو Shell متاحان.
- أن الاختبار داخل Candidate يساوي قبول المصدر.

---

# 16. أوامر وروابط UAT الرئيسية

```text
/agent-console/first-read-only-operation
/agent-console/evidence-workbench
/agent-console/development-pipeline
/agent-console/coding-model
```

الروابط التي ثبتت بصريًا:

```text
/agent-console/first-read-only-operation
/agent-console/development-pipeline
/agent-console/coding-model
```

---

# 17. تعريف النجاح للمرحلة القادمة

نجاح أول تشغيل نموذج برمجي لا يعني جودة النص فقط. يجب أن يثبت:

```text
HUMAN_AUTHORIZATION=CONFIRMED
PROVIDER_SCOPE=LOOPBACK_ONLY
MODEL_OUTPUT=STRICT_JSON
PROMPT_VERSION=RECORDED
MODEL_VERSION=RECORDED
SECRET_VALUE_STORED=FALSE
CANDIDATE_WORKSPACE=ISOLATED
AST_SAFETY_GATE=PASS
DIRECT_ARGV_TESTS=PASS
UNIFIED_DIFF=GENERATED
SOURCE_MUTATION=FALSE
SOURCE_APPLY=BLOCKED
EVIDENCE_COMPLETE=PASS
```

---

# 18. ملف بدء الجلسة الجديدة

أُرفق داخل الحزمة ملف:

```text
PALWAKF_LOCAL_AGENTS_NEXT_SESSION_BOOTSTRAP_PROMPT_R1_20260719.txt
```

يجب رفع ملف التوريث والحزمة إلى الجلسة الجديدة، ثم لصق Prompt البدء كما هو.

---

# 19. إنشاء Source Baseline فعلي على Windows

أُرفق:

```text
CREATE_PALWAKF_LOCAL_AGENTS_SOURCE_BASELINE_SNAPSHOT_R1.ps1
```

وظيفته:

- قراءة Source فقط.
- إنشاء Staging مؤقت.
- استبعاد `.venv`, `node_modules`, caches, backups.
- إنشاء Manifest SHA-256.
- إنشاء ZIP.
- إنشاء SHA-256 للـZIP.
- عدم تعديل المصدر.
- يتطلب Token صريح.

هذا السكربت لا يروج الحالة إلى Accepted؛ هو Snapshot فقط.

---

# 20. الخلاصة الحاكمة النهائية

```text
FORMAL_ACCEPTED_BASELINE=
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719

LATEST_APPLIED_REPAIR=
GOVERNED_CODING_MODEL_PROVIDER_VISUAL_CONTRAST_AND_ACCESSIBILITY_REPAIR_V1

LATEST_TECHNICAL_RESULT=
PASS

LATEST_VISUAL_RESULT=
PASS

LATEST_FULL_PHASE_ACCEPTANCE=
RECORDED

ACCEPTANCE_TOKEN=
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719

MODEL_EXECUTION=
NOT_YET_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION

SOURCE_APPLY=
BLOCKED

NEXT_ENGINEERING_PHASE=
MEGA_BATCH_LOCAL_AGENTS_FIRST_GOVERNED_CODING_MODEL_PROBE_AND_MODEL_GENERATED_CANDIDATE_UAT_V1
```
