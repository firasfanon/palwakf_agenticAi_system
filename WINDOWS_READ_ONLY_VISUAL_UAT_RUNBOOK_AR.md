# Runbook — UAT بصري فعلي على Windows (Read-Only)

## الهدف

إنتاج Screenshot وDOM من التشغيل المحلي الفعلي للواجهة `/agent-console` في Worktree معزول؛ لا تعديل للمصدر الأصلي ولا تشغيل نموذج ولا كتابة React.

## المتطلبات المثبتة

```text
Python = 3.12.10 via .venv\Scripts\python.exe
Browser = Microsoft Edge or Google Chrome
Node/npm = existing accepted local setup
Execution scope = isolated worktree only
```

## التنفيذ

من جذر مشروع `palwakf_local_agents` نفّذ:

```powershell
$projectRoot = (Get-Location).Path

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  ".\scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1" `
  -ProjectRoot $projectRoot `
  -DependencyMode OfflineCache `
  -Port 8877
```

## التحقق اليدوي عند فتح المتصفح

1. افتح `/agent-console/` على عرض مكتبي ثم هاتف.
2. افحص: `workspaces` و`tasks` و`evidence` و`diagnostics`.
3. راقب Network: لا `POST/PUT/PATCH/DELETE`، ولا Authorization، ولا Cookies صادرة من React.
4. احفظ HAR عند طلب الـRunner لذلك.

## نواتج متوقعة

- PNG وDOM لخمس صفحات React على الأقل.
- HTTP 200 لمسارات `/agent-console` المعتمدة.
- `/health` مع جميع flags التنفيذية `false`.
- سجل يثبت أن المصدر الأصلي لم يتغير.

## محاذير

```text
DO NOT RUN AGAINST ORIGINAL audit/local_agents.sqlite
DO NOT ENABLE AGENT_EXECUTION
DO NOT ENABLE PLATFORM_MUTATION
DO NOT ENABLE DATABASE_ACCESS
DO NOT ADD REACT WRITE CONTROLS
```
