[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode='Upgrade'
)
$ErrorActionPreference='Stop'
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$contractPath=Join-Path $PackageRoot 'contracts\workspace_core_source_contract.json'
if(-not(Test-Path $app -PathType Leaf)){throw "APP_PY_NOT_FOUND=$app"}
if(-not(Test-Path $contractPath -PathType Leaf)){throw "SOURCE_CONTRACT_NOT_FOUND=$contractPath"}
$contract=Get-Content $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$fail=@()
foreach($property in $contract.source_files.psobject.Properties){
  $relative=$property.Name
  $expected=[string]$property.Value
  $target=Join-Path $ProjectRoot $relative
  if(-not(Test-Path $target -PathType Leaf)){$fail+="WORKSPACE_CORE_SOURCE_MISSING=$relative";continue}
  $actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if($actual -ne $expected){$fail+="WORKSPACE_CORE_SOURCE_HASH_MISMATCH=$relative"}
}
$appText=Get-Content $app -Raw -Encoding UTF8
$goImport='from .governed_operations import mount_governed_operations'
$goMount='mount_governed_operations(app, project_root=PROJECT_ROOT)'
$wsImport='from .workspace_core import mount_workspace_core'
$wsMount='mount_workspace_core(app, project_root=PROJECT_ROOT)'
$goImportCount=([regex]::Matches($appText,[regex]::Escape($goImport))).Count
$goMountCount=([regex]::Matches($appText,[regex]::Escape($goMount))).Count
$wsImportCount=([regex]::Matches($appText,[regex]::Escape($wsImport))).Count
$wsMountCount=([regex]::Matches($appText,[regex]::Escape($wsMount))).Count
if($goImportCount -ne 1){$fail+="GOVERNED_OPERATIONS_IMPORT_ANCHOR_COUNT=$goImportCount"}
if($goMountCount -ne 1){$fail+="GOVERNED_OPERATIONS_MOUNT_ANCHOR_COUNT=$goMountCount"}
if($wsImportCount -ne 0){$fail+="WORKSPACE_CORE_IMPORT_MUST_BE_ABSENT_COUNT=$wsImportCount"}
if($wsMountCount -ne 0){$fail+="WORKSPACE_CORE_MOUNT_MUST_BE_ABSENT_COUNT=$wsMountCount"}
if($fail.Count){
  "PRECONDITION_FAILURE_COUNT=$($fail.Count)"
  "PRECONDITION_FAILURES=$($fail -join ';')"
  throw 'INSTALL_PRECONDITION_FAILED'
}
$stamp=Get-Date -Format 'yyyyMMddHHmmss'
$backup=Join-Path $ProjectRoot "backups\multi_workspace_core_explicit_app_mount_reconciliation_v1_$stamp"
$preHash=(Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash
$patched=$appText.Replace($goImport,($goImport+[Environment]::NewLine+$wsImport)).Replace($goMount,($goMount+[Environment]::NewLine+$wsMount))
$postImportCount=([regex]::Matches($patched,[regex]::Escape($wsImport))).Count
$postMountCount=([regex]::Matches($patched,[regex]::Escape($wsMount))).Count
if($postImportCount -ne 1 -or $postMountCount -ne 1){throw 'PATCH_CONTRACT_FAILED'}
if($PSCmdlet.ShouldProcess($app,'Backup app.py preimage')){
  New-Item -ItemType Directory -Path (Join-Path $backup 'preimage') -Force | Out-Null
  Copy-Item -LiteralPath $app -Destination (Join-Path $backup 'preimage\app.py') -Force
}
if($PSCmdlet.ShouldProcess($app,'Apply exact workspace-core import and mount')){
  [System.IO.File]::WriteAllText($app,$patched,(New-Object System.Text.UTF8Encoding($false)))
}
if(-not $WhatIfPreference){
  $postHash=(Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash
  $manifest=[ordered]@{
    install_status='COMPLETE'
    target_mutation_scope='APP_PY_ONLY'
    backup_path=$backup
    backup_strategy='EXACT_APP_PY_PREIMAGE_COPY'
    app_preimage_sha256=$preHash
    app_postimage_sha256=$postHash
    app_entrypoint_mutation='EXPLICIT_WORKSPACE_CORE_IMPORT_AND_MOUNT_ONLY'
    workspace_core_source_mutation='NONE'
    policy_packs_mutation='NONE'
    command_center_mutation='NONE'
    governed_operations_mutation='NONE'
    local_sqlite_write='NONE_DURING_INSTALL'
    legacy_migration='NONE'
    model_execution='NONE'
    pilot_execution='NOT_EXECUTED'
  }
  $manifestPath=Join-Path $backup 'install_preimage_manifest.json'
  $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
  "INSTALL_STATUS=COMPLETE"
  "BACKUP_PATH=$backup"
  "BACKUP_MANIFEST_PATH=$manifestPath"
  "BACKUP_STATUS=COMPLETE"
  "APP_PREIMAGE_SHA256=$preHash"
  "APP_POSTIMAGE_SHA256=$postHash"
} else {
  "INSTALL_STATUS=WHATIF_COMPLETE"
  "BACKUP_PATH=$backup"
  "BACKUP_STATUS=PLANNED"
  "APP_PREIMAGE_SHA256=$preHash"
}
"TARGET_MUTATION_SCOPE=APP_PY_ONLY"
"APP_ENTRYPOINT_MUTATION=EXPLICIT_WORKSPACE_CORE_IMPORT_AND_MOUNT_ONLY"
"WORKSPACE_CORE_SOURCE_MUTATION=NONE"
"POLICY_PACKS_MUTATION=NONE"
"COMMAND_CENTER_MUTATION=NONE"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL"
"LEGACY_MIGRATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
