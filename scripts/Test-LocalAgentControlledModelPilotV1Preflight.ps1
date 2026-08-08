[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = "Stop"
$hashes = Get-Content -LiteralPath (Join-Path $PackageRoot "CANDIDATE_SOURCE_HASHES.json") -Raw | ConvertFrom-Json
$app = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\app.py"
if (-not (Test-Path -LiteralPath $app -PathType Leaf)) { throw "APP_ENTRYPOINT_MISSING" }
$appText = Get-Content -LiteralPath $app -Raw -Encoding UTF8
$importCount = [regex]::Matches($appText, 'from \.local_agent_core import mount_local_agent_core').Count
$mountCount = [regex]::Matches($appText, 'mount_local_agent_core\(app, project_root=PROJECT_ROOT\)').Count
$states = @()
foreach ($property in $hashes.preimage.PSObject.Properties) {
  $target = Join-Path $ProjectRoot $property.Name
  $state = "MISSING"
  if (Test-Path -LiteralPath $target -PathType Leaf) {
    $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    $state = if ($actual -eq $property.Value) { "TARGET_EQUALS_PREIMAGE" } else { "TARGET_HASH_MISMATCH" }
  }
  $states += [pscustomobject]@{ RelativePath = $property.Name; State = $state }
}
$configTarget = Join-Path $ProjectRoot "config\local_agent_model_pilot_v1.json"
$modelModuleTarget = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\local_agent_core\model_pilot.py"
$failures = @($states | Where-Object { $_.State -ne "TARGET_EQUALS_PREIMAGE" })
if ($importCount -ne 1) { $failures += "APP_IMPORT_COUNT" }
if ($mountCount -ne 1) { $failures += "APP_MOUNT_COUNT" }
if (Test-Path -LiteralPath $configTarget) { $failures += "PILOT_CONFIG_ALREADY_EXISTS" }
if (Test-Path -LiteralPath $modelModuleTarget) { $failures += "MODEL_PILOT_MODULE_ALREADY_EXISTS" }
$run = Join-Path $env:TEMP ("local_agent_controlled_model_pilot_v1_preflight_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $run -Force | Out-Null
$manifest = Join-Path $run "preflight_preimage_manifest.json"
@{ contract = "LOCAL_AGENT_CONTROLLED_MODEL_PILOT_V1"; app_import_count = $importCount; app_mount_count = $mountCount; source_states = $states; failure_count = $failures.Count } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifest -Encoding UTF8
"===== LOCAL AGENT CONTROLLED MODEL PILOT V1 PREFLIGHT ====="
$states | Format-Table -AutoSize
"APP_LOCAL_AGENT_CORE_IMPORT_COUNT=$importCount"
"APP_LOCAL_AGENT_CORE_MOUNT_COUNT=$mountCount"
"PILOT_CONFIG_PREEXISTS=$(Test-Path -LiteralPath $configTarget)"
"MODEL_PILOT_MODULE_PREEXISTS=$(Test-Path -LiteralPath $modelModuleTarget)"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
"PREFLIGHT_MANIFEST=$manifest"
"PROJECT_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
if ($failures.Count -gt 0) { throw "PREFLIGHT_FAILED=$($failures -join ';')" }
"PREFLIGHT_RESULT=PASS"
