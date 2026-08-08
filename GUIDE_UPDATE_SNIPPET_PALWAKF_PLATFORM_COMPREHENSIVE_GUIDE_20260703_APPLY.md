# ملحق تحديث مطلوب للمرجع الأعلى — 20260703

> يُلحق هذا النص في `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` عند توفر الملف الحاكم في بيئة المشروع.

## PalWakf Local Agents — Apply ضيق لصلابة React القراءة فقط

```text
BATCH_ID = MEGA_BATCH_LOCAL_AGENTS_PRODUCTION_READINESS_AND_AGENT_PERFORMANCE_EVALUATION_V1_NARROW_READ_ONLY_RUNTIME_HARDENING_APPLY
STATUS = APPLIED_IN_ISOLATED_SOURCE_REPLICA_AND_VALIDATED
SCOPE = TWO_FILES_ONLY
```

### التغييران المثبتان

1. `backend/src/palwakf_local_agents/app.py`
   - تمت إضافة imports صريحة لـ `FileResponse` و`StaticFiles`.
   - لا يتم mount لواجهة React إلا إذا وجدت `frontend/dist/index.html` و`frontend/dist/assets/` معًا.
2. `frontend/src/api/client.ts`
   - عميل القراءة يستخدم `credentials: "omit"`.
   - لا يوجد تخزين Browser أو Authorization/Bearer أو طلبات كتابة في `frontend/src` وفق الفحص الساكن.

### أدلة القبول

```text
CANDIDATE_ARTIFACT_INTEGRITY = PASS
PREFLIGHT_HASH_VERIFICATION = PASS
POSTAPPLY_HASH_VERIFICATION = PASS
REACT_READ_ONLY_CONTRACT = PASS
REACT_CONDITIONAL_IMPORT_SMOKE_WITH_SYNTHETIC_DIST = PASS
ONLY_TWO_APPROVED_CODE_FILES_CHANGED = PASS
SERVICE_START = NOT_EXECUTED
NPM_INSTALL / BUILD / BROWSER_UAT = NOT_EXECUTED
MODEL / PILOT / NETWORK / SQLITE_MUTATION = NOT_EXECUTED
```

### حواجز باقية

```text
NO_REACT_WRITE_CONTROL
WRITE_AUTHORIZATION_CLOSURE_REQUIRED remains open
NO_PRODUCTION_CANDIDATE
```

ينتقل المسار التالي فقط بعد تفويض مستقل إلى dependency lock + deterministic build + local browser UAT.
