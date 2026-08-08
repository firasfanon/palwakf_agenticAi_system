[CmdletBinding(SupportsShouldProcess=$true)]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot,[ValidateSet('Upgrade')][string]$Mode='Upgrade')
$ErrorActionPreference='Stop'
$stamp=Get-Date -Format 'yyyyMMddHHmmss'
$backup=Join-Path $ProjectRoot "backups\multi_workspace_core_policy_packs_v1_$stamp"
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$required=@(
'backend\src\palwakf_local_agents\workspace_core\__init__.py',
'backend\src\palwakf_local_agents\workspace_core\contracts.py',
'backend\src\palwakf_local_agents\workspace_core\policy.py',
'backend\src\palwakf_local_agents\workspace_core\store.py',
'backend\src\palwakf_local_agents\workspace_core\router.py',
'backend\src\palwakf_local_agents\workspace_core\static\index.html',
'backend\src\palwakf_local_agents\workspace_core\static\styles.css',
'backend\src\palwakf_local_agents\workspace_core\static\app.js',
'backend\tests\test_workspace_core.py',
'docs\ARCHITECTURE_MULTI_WORKSPACE_CORE_POLICY_PACKS_V1_AR.md',
'docs\SECURITY_CONTRACT_MULTI_WORKSPACE_CORE_POLICY_PACKS_V1.md',
'docs\UAT_MULTI_WORKSPACE_CORE_POLICY_PACKS_V1_AR.md',
'docs\CHANGELOG_MULTI_WORKSPACE_CORE_POLICY_PACKS_V1.md',
'policy_packs\government_strict_v1\policy.json',
'policy_packs\developer_controlled_v1\policy.json',
'policy_packs\client_isolated_v1\policy.json',
'policy_packs\research_read_prepare_v1\policy.json'
)
foreach($rel in $required){if(-not(Test-Path (Join-Path $PackageRoot $rel) -PathType Leaf)){throw "PACKAGE_FILE_MISSING=$rel"}}
$appText=Get-Content $app -Raw -Encoding UTF8
if($appText -notmatch [regex]::Escape('from .governed_operations import mount_governed_operations')){throw 'APP_BASELINE_IMPORT_MISSING'}
if($appText -notmatch [regex]::Escape('mount_governed_operations(app, project_root=PROJECT_ROOT)')){throw 'APP_BASELINE_MOUNT_MISSING'}
if($appText -match [regex]::Escape('mount_workspace_core(app, project_root=PROJECT_ROOT)')){throw 'WORKSPACE_CORE_ALREADY_MOUNTED'}
$planned=@('backend\src\palwakf_local_agents\app.py')+$required
foreach($rel in $planned){$target=Join-Path $ProjectRoot $rel;if($PSCmdlet.ShouldProcess($target,'Backup multi-workspace core preimage')){$dest=Join-Path $backup (Join-Path 'preimage' $rel);New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force|Out-Null;if(Test-Path $target -PathType Leaf){Copy-Item $target $dest -Force}}}
foreach($rel in $required){$src=Join-Path $PackageRoot $rel;$target=Join-Path $ProjectRoot $rel;if($PSCmdlet.ShouldProcess($target,'Install multi-workspace core file')){New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force|Out-Null;Copy-Item $src $target -Force}}
$importOld='from .governed_operations import mount_governed_operations'
$importNew=$importOld+[Environment]::NewLine+'from .workspace_core import mount_workspace_core'
$mountOld='mount_governed_operations(app, project_root=PROJECT_ROOT)'
$mountNew=$mountOld+[Environment]::NewLine+'mount_workspace_core(app, project_root=PROJECT_ROOT)'
$patched=$appText.Replace($importOld,$importNew).Replace($mountOld,$mountNew)
if($PSCmdlet.ShouldProcess($app,'Apply exact workspace core import and mount')){[System.IO.File]::WriteAllText($app,$patched,(New-Object System.Text.UTF8Encoding($false)))}
if(-not $WhatIfPreference){$manifest=[ordered]@{install_status='COMPLETE';backup_path=$backup;install_backup_strategy='EXACT_FILE_PREIMAGE_COPY';app_entrypoint_mutation='EXPLICIT_WORKSPACE_CORE_MOUNT_ONLY';command_center_mutation='NONE';governed_operations_mutation='NONE';local_sqlite_write='NONE_DURING_INSTALL';legacy_migration='NONE';model_execution='NONE';pilot_execution='NOT_EXECUTED';planned_files=$planned};New-Item -ItemType Directory -Path $backup -Force|Out-Null;$manifestPath=Join-Path $backup 'install_preimage_manifest.json';$manifest|ConvertTo-Json -Depth 6|Set-Content $manifestPath -Encoding UTF8;"INSTALL_STATUS=COMPLETE";"BACKUP_PATH=$backup";"BACKUP_MANIFEST_PATH=$manifestPath";"BACKUP_STATUS=COMPLETE"}else{"INSTALL_STATUS=WHATIF_COMPLETE";"BACKUP_PATH=$backup";"BACKUP_STATUS=PLANNED"}
"TARGET_MUTATION_SCOPE=NEW_WORKSPACE_CORE_POLICY_PACKS_TESTS_DOCS_PLUS_EXPLICIT_APP_MOUNT";"APP_ENTRYPOINT_MUTATION=EXPLICIT_WORKSPACE_CORE_MOUNT_ONLY";"COMMAND_CENTER_MUTATION=NONE";"GOVERNED_OPERATIONS_MUTATION=NONE";"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL";"LEGACY_MIGRATION=NONE";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED"
