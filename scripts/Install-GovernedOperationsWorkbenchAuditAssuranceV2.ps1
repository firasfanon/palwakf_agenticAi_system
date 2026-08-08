[CmdletBinding(SupportsShouldProcess=$true)]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot,[ValidateSet('Upgrade')][string]$Mode='Upgrade')
$ErrorActionPreference='Stop'
$relativeFiles=@(
'backend\src\palwakf_local_agents\governed_operations\__init__.py','backend\src\palwakf_local_agents\governed_operations\contracts.py','backend\src\palwakf_local_agents\governed_operations\store.py','backend\src\palwakf_local_agents\governed_operations\router.py','backend\src\palwakf_local_agents\governed_operations\static\index.html','backend\src\palwakf_local_agents\governed_operations\static\styles.css','backend\src\palwakf_local_agents\governed_operations\static\app.js','backend\tests\test_governed_operations.py'
)
$docs=@(
 'README_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2_AR.md',
 'SECURITY_CONTRACT_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2.md',
 'UAT_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2_AR.md',
 'CHANGELOG_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2.md'
)
if($WhatIfPreference){
 'INSTALL_STATUS=WHATIF_COMPLETE'
 'TARGET_MUTATION_SCOPE=GOVERNED_OPERATIONS_MODULE_TESTS_AND_DOCS_ONLY'
 'SOURCE_FILE_MUTATION_COUNT=8'
 'DOC_FILE_MUTATION_COUNT=4'
 'COMMAND_CENTER_MUTATION=NONE'
 'APP_ENTRYPOINT_MUTATION=NONE'
 'LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL'
 'LOCAL_SQLITE_SCHEMA_MIGRATION=ON_FIRST_GOVERNED_OPERATIONS_RUNTIME_ACCESS_ONLY'
 'MODEL_EXECUTION=NONE'
 'PILOT_EXECUTION=NOT_EXECUTED'
 exit 0
}
$backupRoot=Join-Path $ProjectRoot ('backups\governed_operations_workbench_audit_assurance_v2_'+(Get-Date -Format 'yyyyMMddHHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force|Out-Null
$manifest=@{install_status='COMPLETE';backup_strategy='EXACT_FILE_PREIMAGE_COPY';safety_posture=@{MODEL_EXECUTION='NONE';PILOT_EXECUTION='NOT_EXECUTED';PLATFORM_MUTATION='NONE';EXTERNAL_DATABASE_ACCESS='NONE';GIT_WRITE='NONE';DEPLOYMENT='NONE';SECRETS_ACCESS='NONE';MEMORY_WRITE='NONE'};files=@()}
foreach($relative in $relativeFiles){
 $source=Join-Path $PackageRoot $relative
 $target=Join-Path $ProjectRoot $relative
 if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "PACKAGE_FILE_MISSING=$relative"}
 if(-not(Test-Path -LiteralPath $target -PathType Leaf)){throw "TARGET_FILE_MISSING=$relative"}
 $backup=Join-Path $backupRoot $relative
 New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force|Out-Null
 Copy-Item -LiteralPath $target -Destination $backup -Force
 $manifest.files+=@{relative_path=$relative;existed_before=$true;preimage_sha256=(Get-FileHash $target -Algorithm SHA256).Hash}
 New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null
 Copy-Item -LiteralPath $source -Destination $target -Force
}
$docTarget=Join-Path $ProjectRoot 'docs\governed_operations\workbench_audit_assurance_v2'
New-Item -ItemType Directory -Path $docTarget -Force|Out-Null
foreach($doc in $docs){Copy-Item -LiteralPath (Join-Path $PackageRoot ('docs\'+$doc)) -Destination (Join-Path $docTarget $doc) -Force}
$manifestPath=Join-Path $backupRoot 'install_preimage_manifest.json'
$manifest|ConvertTo-Json -Depth 7|Set-Content -LiteralPath $manifestPath -Encoding UTF8
'INSTALL_STATUS=COMPLETE'
"BACKUP_PATH=$backupRoot"
"BACKUP_MANIFEST_PATH=$manifestPath"
'BACKUP_STATUS=COMPLETE'
'INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY'
'TARGET_MUTATION_SCOPE=GOVERNED_OPERATIONS_MODULE_TESTS_AND_DOCS_ONLY'
'SOURCE_FILE_MUTATION_COUNT=8'
'DOC_FILE_MUTATION_COUNT=4'
'APP_ENTRYPOINT_MUTATION=NONE'
'COMMAND_CENTER_MUTATION=NONE'
'LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL'
'LOCAL_SQLITE_SCHEMA_MIGRATION=ON_FIRST_GOVERNED_OPERATIONS_RUNTIME_ACCESS_ONLY'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'PLATFORM_MUTATION=NONE'
'EXTERNAL_DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
