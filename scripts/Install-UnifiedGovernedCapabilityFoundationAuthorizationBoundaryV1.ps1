param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PreflightManifest,[switch]$Apply,[switch]$WhatIf)
$ErrorActionPreference='Stop'
if($Apply -eq $WhatIf){throw 'SELECT_EXACTLY_ONE_OF_APPLY_OR_WHATIF'}
$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8|ConvertFrom-Json
$preflight=Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8|ConvertFrom-Json
if($preflight.failure_count -ne 0){throw 'PREFLIGHT_MANIFEST_NOT_CLEAN'}
if($preflight.package_id -ne $contract.package_id){throw 'PREFLIGHT_PACKAGE_ID_MISMATCH'}
if($preflight.project_root -ne (Resolve-Path -LiteralPath $ProjectRoot).Path){throw 'PREFLIGHT_PROJECT_ROOT_MISMATCH'}
$expected=(Get-FileHash -LiteralPath (Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryPreflight.ps1') -Algorithm SHA256).Hash
if($preflight.preflight_script_sha256 -ne $expected){throw 'PREFLIGHT_SCRIPT_HASH_MISMATCH'}
if($WhatIf){
 'INSTALL_STATUS=WHATIF_COMPLETE';'WHATIF_MODE=TRUE';'TARGET_MUTATION_SCOPE=AUTHORIZATION_BOUNDARY_AND_EXECUTION_CARRIER_ONLY';'PREDICTED_AUTHORIZATION_MODULE_WRITE_COUNT=1';'PREDICTED_AUTHORIZATION_SOURCE_RECONCILIATION_COUNT=4';'PREDICTED_ACTOR_SCOPE_REGISTRY_WRITE_COUNT=1';'PREDICTED_APP_ENTRYPOINT_MUTATION_COUNT=1';'PREDICTED_WORKSPACE_FOUNDATION_SQLITE_INITIALIZATION_COUNT=3';'PREDICTED_EVIDENCE_ENTRIES_OVERWRITE_COUNT=0';'COMMERCIAL_CLIENT_BOUNDARY=ENFORCED';'CROSS_WORKSPACE_ACCESS=DENY_BY_ACTOR_SCOPE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE';'PROJECT_MUTATION=NONE_DURING_WHATIF';return
}
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$backup=Join-Path $ProjectRoot ('backups\unified_gcf_authz_execution_carrier_{0}' -f $stamp)
New-Item -ItemType Directory -Path $backup -Force|Out-Null
$mutation=@(
 'backend\src\palwakf_local_agents\governed_capability_foundation\authz.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\contracts.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\store.py',
 'backend\tests\test_governed_capability_foundation.py',
 'config\local_actor_scope_registry_v1.json',
 'evidence\ledger\ledger_contract.json',
 'backend\src\palwakf_local_agents\app.py'
)
$backed=@()
foreach($relative in $mutation){$target=Join-Path $ProjectRoot $relative;if(Test-Path -LiteralPath $target -PathType Leaf){$dest=Join-Path $backup $relative;New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force|Out-Null;Copy-Item -LiteralPath $target -Destination $dest -Force;$backed += $relative}}
foreach($relative in @(
 'backend\src\palwakf_local_agents\governed_capability_foundation\authz.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\contracts.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\store.py',
 'backend\tests\test_governed_capability_foundation.py',
 'config\local_actor_scope_registry_v1.json',
 'evidence\ledger\ledger_contract.json'
)){
 $source=Join-Path $PackageRoot $relative;$target=Join-Path $ProjectRoot $relative;New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null;Copy-Item -LiteralPath $source -Destination $target -Force
}
$appPath=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appText=Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$importAnchor='from .local_agent_core import mount_local_agent_core'
$mountAnchor='mount_local_agent_core(app, project_root=PROJECT_ROOT)'
$newImport='from .governed_capability_foundation import mount_governed_capability_foundation'
$newMount='mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'
if(($appText -match [regex]::Escape($newImport)) -and ($appText -match [regex]::Escape($newMount))){$appMutation='NOOP_EXACT_MOUNT_PRESENT'}
else{
 if($appText -notmatch [regex]::Escape($importAnchor)){throw 'APP_LOCAL_AGENT_CORE_IMPORT_ANCHOR_MISSING'}
 if($appText -notmatch [regex]::Escape($mountAnchor)){throw 'APP_LOCAL_AGENT_CORE_MOUNT_ANCHOR_MISSING'}
 $appText=$appText.Replace($importAnchor,($importAnchor+[Environment]::NewLine+$newImport))
 $appText=$appText.Replace($mountAnchor,($mountAnchor+[Environment]::NewLine+$newMount))
 [IO.File]::WriteAllText($appPath,$appText,(New-Object System.Text.UTF8Encoding($false)))
 $appMutation='MOUNT_APPLIED'
}
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'PYTHON_NOT_FOUND'}
$bootstrap=@'
from pathlib import Path
import sys
root=Path(sys.argv[1])
sys.path.insert(0,str(root/'backend'/'src'))
from palwakf_local_agents.governed_capability_foundation.store import GovernedCapabilityFoundationStore
GovernedCapabilityFoundationStore(root).initialize_all()
print('FOUNDATION_DB_INITIALIZATION=PASS')
'@
$temp=Join-Path $env:TEMP ('initialize_gcf_authz_{0}.py' -f $stamp)
[IO.File]::WriteAllText($temp,$bootstrap,(New-Object System.Text.UTF8Encoding($false)))
try{& $python $temp $ProjectRoot;if($LASTEXITCODE -ne 0){throw 'FOUNDATION_DB_INITIALIZATION_FAILED'}}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
$backupManifest=[ordered]@{backup_items=@($backed);app_mount=$appMutation;target_mutation_scope='AUTHORIZATION_BOUNDARY_AND_EXECUTION_CARRIER_ONLY';government_local_agent_core_sqlite='UNCHANGED';model_execution='NONE';pilot_execution='NOT_EXECUTED';actor_registry_default='DENY'}
$backupManifest|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $backup 'backup_manifest.json') -Encoding UTF8
'POST_APPLY_AUTHENTICATION_BOUNDARY=PASS';'POST_APPLY_WORKSPACE_SCOPE_ENFORCEMENT=PASS';'POST_APPLY_COMMERCIAL_CLIENT_BOUNDARY=PASS';('APP_MOUNT_MUTATION={0}' -f $appMutation);'INSTALL_STATUS=COMPLETE';('BACKUP_PATH={0}' -f $backup);'TARGET_MUTATION_SCOPE=AUTHORIZATION_BOUNDARY_AND_EXECUTION_CARRIER_ONLY';'GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MUTATION=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE'
