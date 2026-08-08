
[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [ValidateSet("Upgrade")][string]$Mode = "Upgrade"
)
$ErrorActionPreference = "Stop"
$expectedPreimage="FD3A453DE80F034521A30A7AAF2E8F4087D33DBF80756BC6BA9D7576EE98803D"
$expectedPostimage="D83F8709428C047D9229ACD9C232BF1F552A078BBBA42B141D7FF7566006CD1E"
$relative="backend\src\palwakf_local_agents\command_center\static\app.js"
$source=Join-Path $PackageRoot $relative
$target=Join-Path $ProjectRoot $relative
if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "CANDIDATE_APP_JS_NOT_FOUND=$source"}
if(-not(Test-Path -LiteralPath $target -PathType Leaf)){throw "TARGET_APP_JS_NOT_FOUND=$target"}
$preHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
$postHash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if($preHash -ne $expectedPreimage){throw "UNEXPECTED_PREIMAGE_SHA256=$preHash"}
if($postHash -ne $expectedPostimage){throw "UNEXPECTED_CANDIDATE_POSTIMAGE_SHA256=$postHash"}
$stamp=Get-Date -Format 'yyyyMMddHHmmss'
$backupRoot=Join-Path $ProjectRoot "backups\command_center_event_listener_deduplication_closure_v1_$stamp"
$preimage=Join-Path $backupRoot "preimage\$relative"
$manifest=Join-Path $backupRoot "install_preimage_manifest.json"
$record=[ordered]@{
  install_status = if($WhatIfPreference){"WHATIF_COMPLETE"}else{"COMPLETE"}
  backup_strategy = "EXACT_FILE_PREIMAGE_COPY"
  target_relative_path = $relative
  preimage_sha256 = $preHash
  candidate_postimage_sha256 = $postHash
  safety_posture = [ordered]@{MODEL_EXECUTION="NONE";PILOT_EXECUTION="NOT_EXECUTED";PLATFORM_MUTATION="NONE";DATABASE_ACCESS="NONE";GIT_WRITE="NONE";DEPLOYMENT="NONE";SECRETS_ACCESS="NONE";MEMORY_WRITE="NONE"}
}
if($PSCmdlet.ShouldProcess($preimage,"Backup exact preimage")){
  New-Item -ItemType Directory -Path (Split-Path -Parent $preimage) -Force | Out-Null
  Copy-Item -LiteralPath $target -Destination $preimage -Force
}
if($PSCmdlet.ShouldProcess($target,"Install command center event-listener deduplication static asset")){
  Copy-Item -LiteralPath $source -Destination $target -Force
  New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
  $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifest -Encoding UTF8
}
"INSTALL_STATUS=$($record.install_status)"
"BACKUP_PATH=$backupRoot"
"BACKUP_MANIFEST_PATH=$manifest"
"BACKUP_STATUS=$(if($WhatIfPreference){'PLANNED'}else{'COMPLETE'})"
"TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE"
"ROUTER_MUTATION=NONE"
"STORE_MUTATION=NONE"
"COMMAND_CENTER_MUTATION=STATIC_APP_JS_ONLY"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE"
"EVENT_LISTENER_DEDUPLICATION=BOOTSTRAP_ONCE_EVENT_DELEGATION"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
