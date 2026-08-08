---
document_id: LOCAL_AGENTS_COMPREHENSIVE_HANDOFF_20260703_REACT_BUILD_HTTP_UAT
status: ACTIVE_HANDOFF
current_baseline: LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703_REACT_BUILD_HTTP_UAT
---

# ملف توريث شامل — PalWakf Local Agents

## نقطة الاستئناف
```text
CURRENT_STAGE = REACT_LOCK_AND_REAL_DIST_BUILT__HTTP_MOUNT_VERIFIED
BROWSER_RENDERING_STATUS = BLOCKED_BY_EXECUTION_ENVIRONMENT_POLICY
NEXT_RUNTIME_TRUTH = WINDOWS_OR_UNRESTRICTED_BROWSER_UAT_ON_PYTHON_3_12
```

## ما تغير
- أضيف lockfile version 3 لتبعيات React/Vite المثبتة.
- أصبح `frontend/dist` حقيقيًا وموجودًا، ولذلك mount الشرطي في `app.py` فعال عند تشغيل المصدر المطبّق.
- لا تغير في `app.py` أو `client.ts` أو أي route أو سياسة.
- لا توجد `node_modules` أو SQLite جديدة ناتجة عن هذه الدفعة في التسليم. حُفظت فقط ملفات SQLite الموروثة من snapshot السابق، واستُبعدت SQLite التي أُنشئت مؤقتًا أثناء UAT.

## أدلة النجاح
- `npm ci`, `tsc`, `vite build` نجحت.
- Clean build مرتين أنتج نفس بصمات الملفات.
- `/health` أكدت أن flags الثلاثة التشغيلية false و`safety_ok=true`.
- Root ومسارات React والـassets أرجعت HTTP 200 دون Set-Cookie.
- عقد read-only موجود في source وفي bundle المبني.

## الأدلة غير المتاحة
لم يتم browser-rendered UAT لأن Chromium النظامي في بيئة الحاوية ممنوع من كل URL عبر policy؛ هذا ليس خطأ React. لا يجوز تحويله إلى PASS أو تجاوز policy. كما تعذر تنزيل Chromium منفصل بسبب DNS.

## أخطاء/ديون يجب عدم خلطها مع Build
- 6 اختبارات backend فاشلة: test suite لا تطابق عقد workspace-scoped الحالي ووسم UI قديم؛ لا patch في هذه الدفعة.
- 11 write routes بقيت تحتاج closure تفويض موحّد وفق baseline السابق.

## Rollback
```text
DELETE frontend/package-lock.json
DELETE frontend/dist/
REMOVE backups/react_dependency_lock_deterministic_build_and_local_browser_uat_v1_20260703/
```
لا تلمس `app.py` أو `client.ts` في rollback لأنهما من baseline السابق، لا من هذه الدفعة.

## التفويضات اللاحقة المقترحة
1. `AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_WINDOWS_LOCAL_BROWSER_UAT_AND_RUNTIME_EVIDENCE_CAPTURE_V1`
2. `AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_BACKEND_TEST_CONTRACT_RECONCILIATION_AND_WRITE_AUTHORIZATION_CLOSURE_DISCOVERY_V1`
