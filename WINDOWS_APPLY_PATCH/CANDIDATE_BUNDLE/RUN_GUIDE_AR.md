# دليل التشغيل — بعد تفويض Apply منفصل فقط

> لا تطبق هذه الحزمة في مرحلة Candidate الحالية. الأمر التالي مخصص فقط إذا صدر تفويض Apply لاحق.

```powershell
$bundleRoot = "<مسار_الحزمة_بعد_فكها>\PALWAKF_LOCAL_AGENTS_LEGACY_TEST_CONTRACT_MIGRATION_AND_CONTROLLED_POSITIVE_AUTHORIZATION_UAT_V1_DISCOVERY_DESIGN_GOVERNED_EXECUTABLE_CANDIDATE_20260704"

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

القبول لا يتم إلا عند:

```text
FINAL_RESULT=PASS
TARGETED_NEGATIVE_AND_POSITIVE_UAT=PASS
FULL_BACKEND_SUITE=PASS
```
