# PalWakf Local Agents — Comprehensive Baseline
## 2026-07-04 — HAR Filename Reconciliation V1 Accepted

```text
BASELINE_STATUS = READ_ONLY_REACT_RUNTIME_UAT_ACCEPTED
HAR_FILENAME_RECONCILIATION_V1 = ACCEPTED
LOCAL_WINDOWS_APPLY = PASS
POSTAPPLY_STATIC_GATE = PASS
```

## ما هو معتمد

1. **React/TypeScript foundation** مبني محليًا ومثبت بـ`package-lock.json`.
2. **FastAPI mount** الشرطي لمسار `/agent-console/` يعمل على loopback وفق الدليل السابق.
3. عقد React الحالي **قراءة فقط**:
   ```text
   GET_ONLY
   credentials: "omit"
   NO_AUTHORIZATION_LITERAL
   NO_WEB_STORAGE_LITERAL
   ```
4. Browser UAT المحلي السابق مقبول بدليل أرشيف مستقل:
   ```text
   WINDOWS_LOCAL_BROWSER_UAT_20260703T222811Z.zip
   SHA-256 = 9661222299D519D667EAD301E53107C3A063B3919BDEB6B651C7DE0D09E3CF26
   ```
5. Runner الآن يدعم تسوية اسم HAR:
   - يقبل `browser_network.har` مباشرة.
   - عند غيابه، يقبل ملف HAR وحيدًا في Evidence Root ويطبع قرار التسوية.
   - يرفض أكثر من ملف HAR لتجنب اختيار ملف عشوائي.
   - يوثق القرار في `browser_network_har_resolution.json`.

## الدفعات/الإصلاحات المدمجة في هذا الـBaseline

```text
READ_ONLY_RUNTIME_HARDENING
REACT_LOCK_BUILD_HTTP_UAT
WINDOWS_LOCAL_BROWSER_UAT_RUNTIME_EVIDENCE
RUNNER_PARSE_REPAIR_V1
RUNNER_PATH_RESOLUTION_REPAIR_V2
RUNNER_COMPATIBILITY_REPAIR_V3
RUNNER_RUNTIME_DIAGNOSTICS_REPAIR_V4
RUNNER_BROWSER_VERSION_PROBE_REPAIR_V5
RUNNER_NPM_STDERR_REPAIR_V6
NPM_LOCKFILE_REGISTRY_PROVENANCE_REPAIR_V7
RUNNER_WORKTREE_CLEANUP_REPAIR_V8
HAR_FILENAME_RECONCILIATION_V1
```

## أدلة الإغلاق لهذه الدفعة

```text
HAR_FILENAME_RECONCILIATION_V1=PASS
RUNNER_PARSER_ERROR_COUNT=0
STATIC_GATE_PARSER_ERROR_COUNT=0
FINAL_RESULT=PASS
```

## القيود الحاكمة المستمرة

```text
NO_REACT_WRITE_CONTROL
NO_MODEL_EXECUTION
NO_PILOT
NO_DATABASE_ACCESS
NO_PLATFORM_MUTATION
NO_PRODUCTION_PROMOTION
```

## ملاحظة صدق المصدر
هذا الـBaseline الوثائقي يثبت التطبيق والـStatic Gate اللذين نفذا على Windows بناءً على نص مخرجات المستخدم. لا يمثل ZIP مصدرًا كاملاً من جهاز Windows ولا يغني عن الاحتفاظ بنسخة المشروع المحلية وبنسخة الـbackup التي أنشأها الإصلاح.
