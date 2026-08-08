# PalWakf Local Agents — Windows Runtime UAT Harness V1

## التفويض المنفذ ضمن هذه الحزمة

```text
AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY
```

هذه حزمة **Harness** معدّة لتنفيذ UAT الحقيقي على جهاز Windows داخل `git worktree` الذي يحتوي أصلًا على المرشح المطبّق. لا تُعدّ دليل تنفيذ؛ لا توجد في هذه البيئة وصلة إلى مشروع Windows أو تشغيل FastAPI/Edge الحقيقيين.

## ما الذي يفعله الـHarness عند تشغيله محليًا

1. يتحقق من أن المسار هو `git worktree` معزول.
2. يثبت مطابقة الملفات السبعة لـ`POSTIMAGE_SHA256.json`، لا لـPreimage.
3. يمنع أوامر migration/seed ضمن أمر تشغيل FastAPI.
4. ينفذ `npm ci --ignore-scripts --offline` ثم `npm run check` و`npm run build` داخل الـworktree.
5. يشغّل Backend محليًا بأمر صريح يمرره المشغل.
6. ينتظر `GET /health` فقط.
7. يشغّل Edge headless عبر DevTools Protocol لفحص:
   - `/agent-console/` على Desktop وMobile.
   - `/agent-console/workspaces`.
   - `/agent-console/tasks`.
   - `/agent-console/diagnostics`.
8. يحفظ Screenshots وHTML وNetwork Summary وConsole ونتيجة قبول/رفض قابلة للقراءة آليًا.

## ما لا يفعله

```text
SOURCE_PROJECT_MUTATION = NONE
SQLITE_MIGRATION = NONE
CLIENT_DATA_WRITE = NONE
REACT_WRITE = NONE
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NONE
PRODUCTION = NONE
```

## نقطة المصالحة الإلزامية

الحزمة السابقة `Invoke-ProductConsoleReadOnlyApplyV1.ps1` كانت تستدعي Static Gate بعد نسخ الـpayload، بينما الـStatic Gate نفسه يطابق `PREIMAGE_SHA256.json`. للملفات الثلاثة المعدلة، يتعارض ذلك منطقيًا مع postimage؛ لذلك لا يجوز إعادة اعتماد نتيجة `STATIC_GATE_PASS` السابقة من ذلك التسلسل وحده.

هذا الـHarness لا يعدل المشروع ولا يعيد Apply. لكنه يصحح **دليل UAT** للتحقق من `POSTIMAGE_SHA256.json` في حالة الـworktree المطبّق فعلًا.

## نتيجة مقبولة

```text
WINDOWS_RUNTIME_UAT_PASS__BASELINE_ACCEPTANCE_REQUIRES_EVIDENCE_REVIEW
```

ولا يصبح baseline معتمدًا قبل مراجعة `UAT_EXECUTION_STATUS.json` و`BROWSER/BROWSER_UAT_REPORT.json` واللقطات المولدة على Windows.
