# دليل التشغيل — Preflight and Manifest Binding Repair Candidate

## الهدف

تنفيذ Syntax ثم Preflight ثم WhatIf دون أي كتابة داخل المشروع. ينشئ الفحص ملفات أدلة مؤقتة تحت `%TEMP%` فقط.

## الأوامر

بعد التحقق من SHA-256 واستخراج الحزمة، شغّل Runner واحدًا فقط:

```powershell
$runner = Join-Path $package "scripts\Invoke-MegaBatch01To06UnifiedCandidateReadiness.ps1"
& $runner -PackageRoot $package -ProjectRoot $target
```

## النتائج المقبولة

```text
CANDIDATE_SYNTAX_RESULT=PASS
CANDIDATE_PREFLIGHT_WHATIF_RUNTIME_SELF_TEST=PASS
PREFLIGHT_RESULT=PASS
PREFLIGHT_MANIFEST_BINDING=PASS
WHATIF_STATUS=COMPLETE
PROJECT_MUTATION=NONE_DURING_WHATIF
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
```

## نتائج توقف صحيحة

- `BASELINE_HASH_MISMATCH` أو `BASELINE_FILE_MISSING`: توقف؛ لا تستخدم WhatIf.
- `PREFLIGHT_MANIFEST_PACKAGE_ID_MISMATCH` أو أي `...HASH_MISMATCH`: لا تستخدم Manifest، أعد تشغيل Preflight من هذه الحزمة.
- `GOVERNMENT_SQLITE_REQUIRED_PRESENT...`: توقف؛ لا تنشئ SQLite ولا تعدلها يدويًا.

لا يوجد `-Apply` في هذا المرشح.
