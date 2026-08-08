# دليل التشغيل المحلي — Static Gate Reconciliation V1

من جذر المشروع في Windows PowerShell 5.1:

```powershell
$zip = "$env:USERPROFILE\Downloads\PALWAKF_LOCAL_AGENTS_LEGACY_TEST_CONTRACT_STATIC_GATE_RECONCILIATION_V1_20260704.zip"
$stage = Join-Path $env:TEMP "palwakf_legacy_test_static_gate_reconciliation_v1"

Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath $zip -DestinationPath $stage -Force

$repair = Join-Path $stage "PALWAKF_LOCAL_AGENTS_LEGACY_TEST_CONTRACT_STATIC_GATE_RECONCILIATION_V1_20260704\Repair-LegacyTestContractStaticGateReconciliationV1.ps1"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File $repair -ProjectRoot (Get-Location).Path
```

المتوقع:

```text
STATIC_GATE_PARSER_ERROR_COUNT=0
LEGACY_TEST_CONTRACT_STATIC_GATE_RECONCILIATION_V1=PASS
```

ثم نفذ بوابة التحقق:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  ".\scripts\Test-LegacyTestContractMigrationAndPositiveAuthorizationUatV1Static.ps1" `
  -ProjectRoot (Get-Location).Path
```

المتوقع:

```text
scoped_governed_routes=True
governed_authorization_header=True
local_authorization_header=True
FINAL_RESULT=PASS
```

لا تنفذ Runner الكامل بعد قبل تقديم مخرجات الإصلاح والبوابة الساكنة.
