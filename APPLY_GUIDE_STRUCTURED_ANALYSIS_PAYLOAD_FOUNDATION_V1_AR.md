# دليل تطبيق Structured Analysis Payload Foundation V1

> **طبيعة الإجراء:** تطوير محكوم لمخرجات تحليلية منظمة. لا ينفذ أي تغيير على منصة PalWakf أو قاعدة بيانات أو Git أو نشر أو أسرار.

## 1. فك الحزمة خارج مسار المشروع
مثال:
```powershell
$package = "C:\Users\DELL\Desktop\LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1"
$target = "C:\Users\DELL\StudioProjects\palwakf_local_agents"
```

## 2. فحص صياغة الحزمة
```powershell
& "$package\scripts\Test-StructuredAnalysisPayloadFoundationPackageSyntaxV1.ps1" `
  -PackageRoot $package

if ($LASTEXITCODE -ne 0) {
  throw "SAPF_PACKAGE_SYNTAX_GATE_FAILED"
}
```

## 3. إعادة تحقق الـBaseline المجمد
```powershell
& "$target\scripts\Test-ReadOnlyAnalysisPack01V1_3Preflight.ps1" `
  -ProjectRoot $target
if ($LASTEXITCODE -ne 0) { throw "PACK01_PRECHECK_FAILED" }

& "$target\scripts\Test-ReadOnlyAnalysisPack01V1_3.ps1" `
  -ProjectRoot $target
if ($LASTEXITCODE -ne 0) { throw "PACK01_STATIC_GATE_FAILED" }

& "$target\scripts\Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1" `
  -ProjectRoot $target
if ($LASTEXITCODE -ne 0) { throw "PACK01_EVAL_GATE_FAILED" }
```

## 4. فحص Preflight للمرشح
```powershell
& "$package\scripts\Test-StructuredAnalysisPayloadFoundationPreflightV1.ps1" `
  -ProjectRoot $target

if ($LASTEXITCODE -ne 0) {
  throw "SAPF_PREFLIGHT_FAILED"
}
```

## 5. WhatIf فقط
```powershell
& "$package\scripts\Install-StructuredAnalysisPayloadFoundationV1.ps1" `
  -ProjectRoot $target `
  -Mode Upgrade `
  -WhatIf
```

لا تنتقل إلى التطبيق الفعلي إلا إذا ظهرت النتيجة:
```text
INSTALL_STATUS=WHATIF_COMPLETE
REGISTRY_MUTATION=DOCUMENTATION_HANDOFF_SKILL_ONLY
CORE_RUNTIME_MUTATION=NONE
CORE_11_LINE_CONTRACT_MUTATION=NONE
```

## 6. التطبيق الفعلي
```powershell
& "$package\scripts\Install-StructuredAnalysisPayloadFoundationV1.ps1" `
  -ProjectRoot $target `
  -Mode Upgrade

if ($LASTEXITCODE -ne 0) {
  throw "SAPF_INSTALL_FAILED"
}
```

## 7. بوابات ما بعد التطبيق
```powershell
& "$target\scripts\Test-StructuredAnalysisPayloadFoundationV1.ps1" `
  -ProjectRoot $target
if ($LASTEXITCODE -ne 0) { throw "SAPF_STATIC_GATE_FAILED" }

& "$target\scripts\Invoke-StructuredAnalysisPayloadFoundationEvalsV1.ps1" `
  -ProjectRoot $target
if ($LASTEXITCODE -ne 0) { throw "SAPF_EVAL_GATE_FAILED" }

"STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1=PASS"
```

## 8. ما يمنع بعد القبول الأولي
لا تشغّل Ollama ولا تنشئ Pilot Tasks ولا تنقل مهمة إلى `approved` ضمن هذه الخطوة. أولًا احفظ مخرجات البوابات واطلب قرار Pilot مستقل.
