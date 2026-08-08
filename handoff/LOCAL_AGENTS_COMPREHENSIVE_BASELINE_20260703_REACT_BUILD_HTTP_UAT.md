---
document_id: LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703_REACT_BUILD_HTTP_UAT
parent_baseline: LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703
status: AUTHORITATIVE_FOR_REACT_LOCK_BUILD_AND_HTTP_RUNTIME_EVIDENCE_ONLY
prepared_on: 2026-07-03
project_root: C:\\Users\\DELL\\StudioProjects\\palwakf_local_agents
---

# Baseline محدث — React Lock / Build / HTTP Runtime

## الحالة الحاكمة
```text
REACT_TYPESCRIPT_SOURCE = APPLIED
REACT_READ_ONLY_HARDENING = APPLIED
PACKAGE_LOCK = APPLIED
NPM_CI = PASS
REAL_VITE_DIST = GENERATED
REAL_DIST_CONDITIONAL_MOUNT = VERIFIED_BY_LOCAL_HTTP
HTTP_ROUTE_UAT = PASS
BROWSER_RENDERED_UAT = BLOCKED_BY_ENVIRONMENT_POLICY
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
REACT_WRITE_CONTROL = NOT_ENABLED
PRODUCTION_DEPLOYMENT = NOT_EXECUTED
PRODUCTION_PROMOTION = NOT_APPROVED
```

## النطاق الفعلي للمصدر
لا تعديل على أي ملف code. الفروقات المسموح بها والمثبتة هي:
```text
frontend/package-lock.json
frontend/dist/index.html
frontend/dist/assets/index-BLhDdh2Z.css
frontend/dist/assets/index-BPZmFY1Y.js
backups/react_dependency_lock_deterministic_build_and_local_browser_uat_v1_20260703/preimage/package.json
```

## العقد الأمني الباقي
```text
NO_REACT_WRITE_CONTROL
NO_FRONTEND_TOKEN_PERSISTENCE
NO_COOKIE_CREDENTIALS_FROM_REACT_READ_CLIENT
NO_MODEL_EXECUTION
NO_PILOT
NO_DEPLOYMENT
```

## الاختبارات
```text
npm ci --ignore-scripts --no-audit --no-fund = PASS
npm run check = PASS
npm run build = PASS
repeated clean build manifest comparison = PASS
real dist HTTP mount = PASS
backend pytest = 33 passed / 6 failed
browser rendered UAT = BLOCKED_BY_ENVIRONMENT_POLICY
```

## الحواجز المفتوحة
1. `ER-PRR-003`: توحيد تفويض مسارات الكتابة الخادمية لا يزال مطلوبًا؛ لا React writes.
2. `ER-RBU-001`: بيئة UAT الحالية تمنع browser-rendered verification بسياسة متصفح عامة.
3. `ER-RBU-002`: انحراف/تعارض عقد test suite مع governed_operations workspace-scoped runtime.
4. `ER-RBU-003`: baseline المحلي المرجعي يستهدف Python 3.12 بينما بيئة الفحص الحالية Python 3.13.5.

## نقطة الاستئناف
يلزم أولًا Browser UAT على جهاز محلي طبيعي أو بيئة متصفح غير محجوبة، وبايثون 3.12 عند اختبار backend. لا يمنح هذا الـbaseline صلاحية Production أو Pilot أو React write.
