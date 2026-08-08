# Runbook — Windows Runtime UAT (Read-Only)

## شروط البدء

- نفّذ من PowerShell 7 أو Windows PowerShell على جهاز Windows.
- لديك مسار `git worktree` عزلت داخله المرشح وطبقت فيه الملفات السبعة المطابقة للـPostimage.
- استخرج مرشح UX/UI السابق إلى مسار محلي؛ يلزم وجود `POSTIMAGE_SHA256.json` و`PATCH_MANIFEST.json` فيه.
- يجب معرفة أمر تشغيل FastAPI المحلي الصحيح للمشروع. لا تُخمّن المسار أو اسم module.
- يجب أن يكون Edge وNode متاحين (`msedge.exe`, `node.exe`).

## مثال تشغيل

> استبدل القيم بين الأقواس حسب جهازك. أمر الـBackend مثال هيكلي فقط؛ استخدم أمر المشروع الحقيقي غير المهاجر.

```powershell
$worktree = 'C:\Users\DELL\StudioProjects\palwakf_local_agents_uat_worktree'
$candidate = 'D:\PALWAKF_ASSISTANT_BASELINES\PALWAKF_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_UX_UI_READ_ONLY_CANDIDATE_V1_20260706\PALWAKF_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_UX_UI_READ_ONLY_CANDIDATE_V1_20260706'
$output = 'D:\PALWAKF_ASSISTANT_BASELINES\LOCAL_AGENTS_PRODUCT_CONSOLE_WINDOWS_UAT_20260707'
$backend = 'python -m uvicorn <PROJECT_MODULE>:app --host 127.0.0.1 --port 8787'

Set-ExecutionPolicy -Scope Process Bypass -Force
& '.\scripts\Invoke-ProductConsoleReadOnlyWindowsRuntimeUatV1.ps1' `
  -WorktreePath $worktree `
  -CandidateRoot $candidate `
  -BackendStartCommand $backend `
  -OutputDirectory $output `
  -BaseUrl 'http://127.0.0.1:8787'
```

## أدلة الإخراج المطلوبة

```text
UAT_EXECUTION_STATUS.json
BROWSER/BROWSER_UAT_REPORT.json
BROWSER/NETWORK_SUMMARY.json
BROWSER/CONSOLE.json
BROWSER/START_DESKTOP.png
BROWSER/START_MOBILE.png
BROWSER/WORKSPACES_DESKTOP.png
BROWSER/TASKS_DESKTOP.png
BROWSER/DIAGNOSTICS_DESKTOP.png
BROWSER/*.html
NPM_CI_OFFLINE.log
TSC_NO_EMIT.log
VITE_BUILD.log
BACKEND_STDOUT.log
BACKEND_STDERR.log
```

## معايير القبول

```text
POSTIMAGE_VALIDATION = PASS
SOURCE_SCOPE = PASS
BACKEND_COMMAND_GATE = PASS
HEALTH_GET = PASS
RTL_RENDER = PASS
DESKTOP_NAVIGATION = PASS
MOBILE_DRAWER = PASS
NO_MOBILE_NAV_STACKING = PASS
NO_RAW_JSON_PRIMARY_SURFACE = PASS
GET_ONLY_NETWORK = PASS
CREDENTIALS_OMIT_OBSERVED = PASS
NO_REACT_WRITE = PASS
NO_MODEL_OR_PILOT_EXECUTION = PASS
CONSOLE_ERRORS = PASS
RESULT = WINDOWS_RUNTIME_UAT_PASS
```

## رفض مباشر

- أي `POST/PUT/PATCH/DELETE` مصدره المتصفح.
- أي `Authorization` أو `Cookie` ضمن طلب React Fetch/XHR.
- ظهور `console error`.
- فشل Drawer على عرض `390px` أو تكدس الشريط الجانبي فوق المحتوى.
- عدم تطابق Postimage أو أي تغير مصدر داخل `frontend/src` خارج الملفات السبعة.
- أي تشغيل migration أو seed أو model أو pilot.
