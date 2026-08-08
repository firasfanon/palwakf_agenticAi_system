# Windows Run Guide

من جذر المشروع المحلي وبعد فك `WINDOWS_APPLY_PATCH/CANDIDATE_BUNDLE` إلى مجلد مؤقت:

```powershell
$bundleRoot = "<TEMP>\PALWAKF_LOCAL_AGENTS_LEGACY_TEST_CONTRACT_MIGRATION_AND_CONTROLLED_POSITIVE_AUTHORIZATION_UAT_V1_DISCOVERY_DESIGN_GOVERNED_EXECUTABLE_CANDIDATE_20260704"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "$bundleRoot\scripts\Apply-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1" `
  -ProjectRoot (Get-Location).Path

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  ".\scripts\Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1" `
  -ProjectRoot (Get-Location).Path

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  ".\scripts\Run-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1" `
  -ProjectRoot (Get-Location).Path
```

القبول المحلي يتطلب: `FINAL_RESULT=PASS`, و`TARGETED_NEGATIVE_AND_POSITIVE_UAT=PASS`, و`FULL_BACKEND_SUITE=PASS`.
