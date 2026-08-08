---
document_id: LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703
title: Baseline شامل ومحدث — PalWakf Local Agents
language: ar
status: AUTHORITATIVE_TECHNICAL_BASELINE_FOR_NEXT_GATED_STAGE
evidence_cutoff: 2026-07-03
prepared_on: 2026-07-03
project_root: C:\Users\DELL\StudioProjects\palwakf_local_agents
parent_baseline: LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260702
---

# Baseline شامل ومحدث — PalWakf Local Agents

## 1. المرجع والحالة الحاكمة

يستبدل هذا الـBaseline المرجع التنفيذي السابق `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260702` في حدود ما تم إثباته في هذه الدفعة فقط. لا يوجد ملف `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` ضمن الإدخالات المتاحة؛ لذلك أُرفق ملحق تحديث جاهز ولا يُدّعى تعديل المرجع الأعلى مباشرة.

```text
GOVERNED_PLATFORM_FOUNDATION = APPLIED_AND_ACCEPTED
MULTI_WORKSPACE_ISOLATION = APPLIED_AND_ACCEPTED
DEFAULT_DENY_RUNTIME = APPLIED_AND_ACCEPTED
EVIDENCE_LEDGER = ACTIVE
LEGACY_STATIC_FRONTEND_V1 = APPLIED_STATICALLY
REACT_TYPESCRIPT_SOURCE = APPLIED_AND_ACCEPTED
REACT_READ_ONLY_RUNTIME_HARDENING = APPLIED_AND_VALIDATED_IN_ISOLATED_REPLICA
REACT_RUNTIME_BUILD = NOT_BUILT
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
PRODUCTION_DEPLOYMENT = NOT_EXECUTED
```

## 2. الدفعة الأخيرة المقبولة

```text
MEGA_BATCH_LOCAL_AGENTS_PRODUCTION_READINESS_AND_AGENT_PERFORMANCE_EVALUATION_V1_NARROW_READ_ONLY_RUNTIME_HARDENING_APPLY
```

### النطاق المنفذ

| الملف | التغيير المقبول | النتيجة |
|---|---|---|
| `backend/src/palwakf_local_agents/app.py` | imports صريحة + شرط `dist/index.html` و`dist/assets/` قبل mount | PASS |
| `frontend/src/api/client.ts` | `credentials: "omit"` لعميل GET | PASS |

```text
PREIMAGE_HASH = PASS
POSTIMAGE_HASH = PASS
REACT_READ_ONLY_CONTRACT = PASS
CONDITIONAL_REACT_IMPORT_SMOKE = PASS
ONLY_TWO_APPROVED_CODE_FILES_CHANGED = PASS
```

### حدود الدليل

اختبار import استخدم `frontend/dist` اصطناعيًا مؤقتًا داخل نسخة منعزلة ثم حُذف؛ لم ينشأ `dist` حقيقي ولم يبدأ خادم. لم تتغير نسخة المشروع الفعلية على جهاز المستخدم من داخل هذه الجلسة؛ artifact المصدر المطبق هو نسخة مخرجة قابلة للتسليم والتطبيق المحلي المنضبط.

## 3. الحوكمة وWorkspaces

```text
ALLOW = authenticated actor
        AND actor scope
        AND workspace scope
        AND (commercial => client scope)
        AND policy allows operation
ELSE = DENY
```

قواعد الحظر باقية:

```text
NO_DEFAULT_ACTOR
NO_DEFAULT_TOKEN
NO_UNSCOPED_WORKSPACE_READ
NO_CROSS_WORKSPACE_WRITE
NO_CROSS_CLIENT_COMMERCIAL_ACCESS
NO_FRONTEND_TOKEN_PERSISTENCE
NO_COOKIE_CREDENTIALS_FROM_REACT_READ_CLIENT
NO_WRITE_UI_UNTIL_SERVER_AUTHZ_IS_PROVEN
```

## 4. React/TypeScript/Vite

### مثبت ومقبول

```text
Arabic RTL application shell = PRESENT
read-only typed API client = PRESENT
conditional /agent-console mount = PRESENT
legacy static fallback = PRESERVED
credentials omit = ENFORCED_FOR_CURRENT_READ_CLIENT
frontend token/storage scan = PASS
frontend write-request scan = PASS
```

### غير منفذ قطعًا

```text
npm install = NOT_EXECUTED
package-lock.json = NOT_GENERATED
npm run build = NOT_EXECUTED
frontend/dist real build = NOT_GENERATED
service start = NOT_EXECUTED
browser UAT = NOT_EXECUTED
```

## 5. Backend وحالة التفويض

الـBackend يحتوي على المسارات الأساسية: health، workspaces، agents، tasks، projects، evidence، reviews، preparations، pilot controls، diagnostics، وgoverned capability foundation.

سجل AST الساكن للدّفعة الحالية أحصى:

```text
WRITE_ROUTE_COUNT = 15
WRITE_AUTHORIZATION_CLOSURE_REQUIRED = 11
WRITE_REQUIRES_NEGATIVE_UAT = 4
```

لذلك يظل القرار:

```text
NO_REACT_WRITE_CONTROL
NO_WRITE_BINDING
NO_PRODUCTION_CANDIDATE
```

## 6. المساعد والتقييم

```text
provider = ollama local loopback
configured model = qwen2.5:3b
model execution = NONE
pilot execution = NOT_EXECUTED
```

لا يُنفذ أي prompt أو evaluation live قبل تفويض مستقل، fixtures معتمدة، reviewer مسمى، evidence manifest، وشروط stop/rollback.

## 7. الأدلة والاسترجاع

### دليل الدفعة الحالية

المخرجات المطلوبة موجودة داخل حزمة Apply Evidence/Handoff المرافقة:

```text
candidate integrity
preflight hash proof
postapply hash proof
React read-only contract proof
conditional import smoke proof
API authorization static inventory
mutation scope proof
rollback manifest
```

### الاسترجاع

```text
backup = backups/production_readiness_read_only_runtime_hardening_20260703_010000
restore = explicit human decision only
rollback scope = exact two files only
```

### فجوة باقية

```text
PREVIOUS_TEMP_EVIDENCE_RETENTION = OPEN_RISK
DURABLE_ARCHIVE_MIGRATION = NOT_EXECUTED
```

## 8. Error Record

| المعرف | الحالة |
|---|---|
| ER-PRR-001 — React import blocker | RESOLVED_AND_VALIDATED |
| ER-PRR-002 — cookie credentials risk | RESOLVED_AND_VALIDATED |
| ER-PRR-003 — unified write authorization | OPEN_BLOCKER |

## 9. الحظر الصريح

```text
DO_NOT_RUN npm install
DO_NOT_RUN npm run build
DO_NOT_START service
DO_NOT_RUN browser UAT
DO_NOT_EXECUTE model prompt
DO_NOT_EXECUTE pilot
DO_NOT_ENABLE React writes
DO_NOT_ENABLE autonomous task execution
DO_NOT_DEPLOY
DO_NOT_PROMOTE_TO_PRODUCTION
```

## 10. نقطة الاستئناف والتفويض التالي

التفويض التالي المقترح، منفصل تمامًا عن هذه الدفعة:

```text
AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_REACT_DEPENDENCY_LOCK_DETERMINISTIC_BUILD_AND_LOCAL_BROWSER_UAT_V1
```

لا ينفذ هذا التفويض المقترح نموذجًا أو Pilot أو مسارات كتابة React؛ يقتصر على dependency lock، install/build محكوم، verification للـdist، local service/browser UAT، وevidence/rollback.
