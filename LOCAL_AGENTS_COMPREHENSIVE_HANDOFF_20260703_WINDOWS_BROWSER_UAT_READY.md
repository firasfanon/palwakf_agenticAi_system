---
document_id: LOCAL_AGENTS_COMPREHENSIVE_HANDOFF_20260703_WINDOWS_BROWSER_UAT_READY
status: SESSION_HANDOFF
---

# Session Handoff شامل

## آخر Baseline

`LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703_WINDOWS_BROWSER_UAT_READY`

## التغيرات في هذه الدفعة

إضافة أدوات Windows UAT فقط، مع تقرير تنفيذ وتحقيق ساكن مثبتين داخل baseline. الحزمة لا تغيّر التطبيق؛ تشغله داخل Worktree مستنسخ وتضع الدليل في `output/windows_local_browser_uat/`.

## التنفيذ التالي الإلزامي

```powershell
.\scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1
.\scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1 -DependencyMode OfflineCache
```

عند فشل offline dependency cache فقط، استخدم `-DependencyMode Registry` بعد قبول الأثر الشبكي المحدود لحزم مقفلة مسبقًا.

## Evidence gate

لا تعتبر UAT مكتملة إلا عند وجود:

- archive ZIP وبصمة SHA-256.
- `health.json` سليم.
- HTTP results بلا Set-Cookie.
- screenshots/DOM.
- `browser_network.har` وتحليل `PASS`.
- عدم تغير hashes للملفات المتعقبة في المصدر الأصلي.

## الحواجز المفتوحة

1. Browser UAT الحقيقي على Windows pending.
2. backend Legacy test reconciliation (`33/6` في الدفعة السابقة).
3. server-side write authorization closure لمسارات Legacy.
4. Production وModel/Pilot محظورة.
