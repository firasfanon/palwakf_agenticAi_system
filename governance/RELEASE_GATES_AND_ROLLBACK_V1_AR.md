# بوابات الإصدار والRollback — V1

## قاعدة عامة

لا يعتبر نجاح Parse أو Static scan أو وجود `dist` موافقة إنتاجية. الموافقة تتطلب أدلة موزونة لكل بوابة.

## مصفوفة البوابات

| Gate | القبول | حالة المرشح |
|---|---|---|
| `G0` | candidate hashes، source baseline unchanged، scope documented | PASS |
| `G1` | preflight exact hash، backup، Apply narrow، postimage validation | PENDING |
| `G2` | dependency provenance، lockfile، `npm ci`/install evidence، check/build | PENDING |
| `G3` | local import smoke، route activation، desktop/narrow RTL UAT، legacy fallback | PENDING |
| `G4` | all write APIs possess actor/workspace/client enforcement and negative UAT | PENDING |
| `G5` | evaluation fixture results, human rubric, immutable evidence manifests | PENDING |
| `G6` | one controlled pilot with explicit scope/reviewer/stop conditions | PENDING |
| `G7` | release approver, rollback rehearsal, observability, retention archive | PENDING |

## شروط إيقاف فوري

```text
HASH_MISMATCH
UNSCOPED_WRITE_REACT_BINDING
CROSS_WORKSPACE_OR_CROSS_CLIENT_LEAK
COOKIE_OR_TOKEN_PERSISTENCE
MODEL_EXECUTION_WITHOUT_EXPLICIT_AUTHORIZATION
MISSING_EVIDENCE_MANIFEST
BROWSER_UAT_POLICY_FAILURE
```

## Rollback

- إصلاحا G1 موضعيان ومحددان بملفين فقط.
- `Apply-Candidate.ps1` ينشئ نسخة احتياطية زمنية قبل أي كتابة.
- لا يستخدم Rollback restore إلا بعد قرار صريح؛ لا يوجد rollback تلقائي.
- لا تمس الحزمة `frontend/dist` أو SQLite أو policy packs أو Legacy static assets.
