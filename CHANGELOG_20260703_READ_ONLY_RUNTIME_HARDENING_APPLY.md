# Changelog — 20260703 — Read-Only Runtime Hardening Apply

## الحالة

```text
APPLY_STATUS = PASS_IN_ISOLATED_SOURCE_REPLICA
ORIGINAL_USER_LOCAL_PROJECT_MUTATION = NOT_PERFORMED_FROM_THIS_SESSION
```

## تغييرات المصدر المضبوطة

1. `backend/src/palwakf_local_agents/app.py`
   - imports لـ `FileResponse` و`StaticFiles`.
   - لا يتم mount لمسار `/agent-console` إلا بوجود index وassets معًا.
2. `frontend/src/api/client.ts`
   - `credentials: "same-origin"` ← `credentials: "omit"`.

## أدلة النجاح

```text
CANDIDATE_INTEGRITY = PASS
PREFLIGHT = PASS
POSTAPPLY = PASS
READ_ONLY_CONTRACT = PASS
SYNTHETIC_DIST_IMPORT_SMOKE = PASS
MUTATION_SCOPE = PASS
```

## غير منفذ

```text
npm install / lock / build / service / browser / model / pilot / SQLite / network = NOT_EXECUTED
```

## حواجز باقية

```text
WRITE_AUTHORIZATION_CLOSURE_REQUIRED = 11
NO_REACT_WRITE_CONTROL = ENFORCED
PRODUCTION_CANDIDATE = NOT_GRANTED
```
