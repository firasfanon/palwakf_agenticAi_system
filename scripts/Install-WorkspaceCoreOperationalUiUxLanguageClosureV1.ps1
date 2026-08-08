[CmdletBinding(SupportsShouldProcess=$true)]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot,[ValidateSet('Upgrade')][string]$Mode='Upgrade')
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMddHHmmss'
$backup=Join-Path $ProjectRoot "backups\workspace_core_operational_ui_ux_language_closure_v1_$stamp"
$required=@(
  'backend\src\palwakf_local_agents\workspace_core\static\index.html',
  'backend\src\palwakf_local_agents\workspace_core\static\styles.css',
  'backend\src\palwakf_local_agents\workspace_core\static\app.js',
  'backend\tests\test_workspace_core.py',
  'docs\WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1_AR.md',
  'docs\UAT_WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1_AR.md',
  'docs\CHANGELOG_WORKSPACE_CORE_OPERATIONAL_UI_UX_LANGUAGE_CLOSURE_V1.md'
)
foreach($rel in $required){if(-not(Test-Path (Join-Path $PackageRoot $rel) -PathType Leaf)){throw "PACKAGE_FILE_MISSING=$rel"}}
$preflight=Join-Path $PackageRoot 'scripts\Test-WorkspaceCoreOperationalUiUxLanguageClosureV1Preflight.ps1'
if(-not(Test-Path $preflight -PathType Leaf)){throw 'PREFLIGHT_SCRIPT_MISSING'}
& $preflight -ProjectRoot $ProjectRoot -PackageRoot $PackageRoot
if($LASTEXITCODE -ne 0){throw 'PREFLIGHT_FAILED'}
foreach($rel in $required){
  $target=Join-Path $ProjectRoot $rel
  if($PSCmdlet.ShouldProcess($target,'Backup workspace-core UI preimage')){
    $dest=Join-Path $backup (Join-Path 'preimage' $rel)
    New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force|Out-Null
    if(Test-Path $target -PathType Leaf){Copy-Item $target $dest -Force}
  }
}
foreach($rel in $required){
  $src=Join-Path $PackageRoot $rel
  $target=Join-Path $ProjectRoot $rel
  if($PSCmdlet.ShouldProcess($target,'Install workspace-core UI closure file')){
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force|Out-Null
    Copy-Item $src $target -Force
  }
}
if(-not $WhatIfPreference){
  $manifest=[ordered]@{
    install_status='COMPLETE'
    backup_path=$backup
    install_backup_strategy='EXACT_FILE_PREIMAGE_COPY'
    target_mutation_scope='WORKSPACE_CORE_UI_ASSETS_TESTS_AND_DOCS_ONLY'
    app_entrypoint_mutation='NONE'
    core_api_mutation='NONE'
    policy_pack_mutation='NONE'
    command_center_mutation='NONE'
    governed_operations_mutation='NONE'
    local_sqlite_write='NONE_DURING_INSTALL'
    model_execution='NONE'
    pilot_execution='NOT_EXECUTED'
    planned_files=$required
  }
  New-Item -ItemType Directory -Path $backup -Force|Out-Null
  $manifestPath=Join-Path $backup 'install_preimage_manifest.json'
  $manifest|ConvertTo-Json -Depth 5|Set-Content $manifestPath -Encoding UTF8
  "INSTALL_STATUS=COMPLETE";"BACKUP_PATH=$backup";"BACKUP_MANIFEST_PATH=$manifestPath";"BACKUP_STATUS=COMPLETE"
}else{
  "INSTALL_STATUS=WHATIF_COMPLETE";"BACKUP_PATH=$backup";"BACKUP_STATUS=PLANNED"
}
"TARGET_MUTATION_SCOPE=WORKSPACE_CORE_UI_ASSETS_TESTS_AND_DOCS_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE";"CORE_API_MUTATION=NONE";"POLICY_PACK_MUTATION=NONE";"COMMAND_CENTER_MUTATION=NONE";"GOVERNED_OPERATIONS_MUTATION=NONE";"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED"
