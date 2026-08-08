---
document_id: UAT_REACT_WINDOWS_LOCAL_BROWSER_RUNTIME_EVIDENCE_V1
status: AUTHORIZED_EXECUTION_RUNBOOK
scope: Windows local-only runtime, rendered browser UAT, HAR evidence, screenshot/DOM capture
---

# UAT المحلي على Windows لواجهة React وأدلة التشغيل

## الهدف

إثبات أن واجهة React المركبة تحت `/agent-console/` تعمل على Windows محليًا عبر `127.0.0.1`، وتبقى طبقة قراءة فقط، مع دليل قابل للأرشفة على HTTP، وصور/DOM متصفح فعلي، وHAR من جلسة المتصفح.

## الحدود الحاكمة

- لا تشغيل نموذج أو Pilot.
- لا Platform mutation أو Database access خارجي.
- لا React write ولا `POST/PUT/PATCH/DELETE` صادر من عميل React.
- لا `Authorization` أو `Bearer` أو Cookies من عميل React.
- تشغيل FastAPI وSQLite الناتج عن startup يقع داخل Worktree مؤقت فقط؛ لا يجوز تشغيله على ملف `audit/local_agents.sqlite` الأصلي.
- لا يمنح نجاح هذه الدفعة أي اعتماد Production أو تفويض لمسارات Legacy ذات الكتابة.

## المتطلبات

| بند | المطلوب |
|---|---|
| النظام | Windows 10/11 محلي |
| Python | 3.11 أو 3.12 فقط، مع FastAPI/Uvicorn مثبتين في `.venv` أو في `PythonExe` الممرر |
| Node/npm | مثبتان؛ توثَّق النسخ الفعلية داخل الدليل |
| Browser | Microsoft Edge أو Google Chrome محلي |
| Dependencies | يستخدم `npm ci --ignore-scripts` من `frontend/package-lock.json` فقط |

## التشغيل

نفّذ أولًا فحص الحزمة:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1
```

ثم نفّذ UAT الافتراضي دون الوصول إلى Registry:

```powershell
.\scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1 -DependencyMode OfflineCache
```

إذا فشل `OfflineCache` لغياب حزم npm المحلية فقط، يجوز إجراء مستقل ومصرّح به بتشغيل:

```powershell
.\scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1 -DependencyMode Registry
```

هذا الخيار قد يصل إلى npm Registry لتثبيت ما هو مقفل أصلًا في `package-lock.json`. لا تستخدم `npm install` أو تعديل الإصدارات.

## الدليل اليدوي الإلزامي

عندما يفتح المتصفح:

1. راجع `/agent-console/` ثم التنقل إلى Workspaces وTasks وEvidence وDiagnostics.
2. افتح DevTools > Network، وفعل **Preserve log**، ثم أعد تحميل الصفحة.
3. صدّر الشبكة بصيغة HAR إلى المسار الذي يعرضه Runner:
   ```text
   output/windows_local_browser_uat/<RUN_ID>/browser_network.har
   ```
4. أغلق نافذة المتصفح المعزولة، ثم أكمل الـRunner.

## قواعد القبول

| البوابة | قبول |
|---|---|
| Build | `npm ci`, `npm run check`, `npm run build` تنجح في Worktree |
| Safety | `/health` يثبت جميع flags التشغيلية `false` |
| HTTP | كل مسارات React والـassets ترجع `200`، من دون `Set-Cookie` |
| Negative execution | `POST /api/tasks/UAT-NOOP/run` يرجع `403` فقط |
| Render | تُنتج PNG وDOM لخمسة مسارات React |
| HAR | لا طلبات كتابة، لا Authorization، لا Set-Cookie |
| Integrity | hashes للملفات المتعقبة في المصدر الأصلي لم تتغير |

غياب HAR لا يفشل HTTP أو Screenshot evidence، لكنه يمنع اعتماد **Browser Network Evidence** الكامل ويجعل النتيجة `PARTIAL_ACCEPTANCE`.
