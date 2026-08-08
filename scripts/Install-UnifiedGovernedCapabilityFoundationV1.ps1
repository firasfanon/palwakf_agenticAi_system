param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PreflightManifest,[switch]$Apply,[switch]$WhatIf)
$ErrorActionPreference='Stop'
if($Apply -eq $WhatIf){throw 'SELECT_EXACTLY_ONE_OF_APPLY_OR_WHATIF'}
$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$preflight=Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if($preflight.failure_count -ne 0){throw 'PREFLIGHT_MANIFEST_NOT_CLEAN'}
if($preflight.package_id -ne $contract.package_id){throw 'PREFLIGHT_PACKAGE_ID_MISMATCH'}
if($preflight.project_root -ne (Resolve-Path -LiteralPath $ProjectRoot).Path){throw 'PREFLIGHT_PROJECT_ROOT_MISMATCH'}
$expectedScriptHash=(Get-FileHash -LiteralPath (Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationPreflight.ps1') -Algorithm SHA256).Hash
if($preflight.preflight_script_sha256 -ne $expectedScriptHash){throw 'PREFLIGHT_SCRIPT_HASH_MISMATCH'}
$changes=@(
 'workspaces\palwakf_government\workspace_manifest.json',
 'evidence\ledger\ledger_contract.json',
 'evidence\ledger\entries.jsonl',
 'config\controlled_first_prompt_pilot_v1.json',
 'backend\src\palwakf_local_agents\governed_capability_foundation\__init__.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\contracts.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\tools.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\store.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py',
 'backend\tests\test_governed_capability_foundation.py',
 'backend\src\palwakf_local_agents\app.py',
 'workspaces\personal_development\capability_foundation.sqlite',
 'workspaces\commercial_projects\capability_foundation.sqlite',
 'workspaces\research_learning\capability_foundation.sqlite'
)
if($WhatIf){
 'INSTALL_STATUS=WHATIF_COMPLETE';'WHATIF_MODE=TRUE';'TARGET_MUTATION_SCOPE=MB1_TO_MB5_AND_MB6_CONFIGURATION_ONLY';'PREDICTED_GOVERNMENT_MANIFEST_WRITE_COUNT=1';'PREDICTED_EVIDENCE_LEDGER_FILE_COUNT=2';'PREDICTED_CAPABILITY_SOURCE_FILE_COUNT=6';'PREDICTED_WORKSPACE_FOUNDATION_SQLITE_COUNT=3';'PREDICTED_PILOT_CONFIG_WRITE_COUNT=1';'PREDICTED_APP_ENTRYPOINT_MUTATION_COUNT=1';'MB6_MODEL_PROMPT_DURING_APPLY=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE';'PROJECT_MUTATION=NONE_DURING_WHATIF';return
}
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$backup=Join-Path $ProjectRoot ("backups\\unified_governed_capability_foundation_v1_{0}" -f $stamp)
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$backupItems=@()
foreach($relative in $changes){$target=Join-Path $ProjectRoot $relative;if(Test-Path -LiteralPath $target -PathType Leaf){$destination=Join-Path $backup $relative;New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null;Copy-Item -LiteralPath $target -Destination $destination -Force;$backupItems += $relative}}
$packageSource=Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_capability_foundation'
$targetSource=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_capability_foundation'
Copy-Item -LiteralPath $packageSource -Destination $targetSource -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'backend\tests\test_governed_capability_foundation.py') -Destination (Join-Path $ProjectRoot 'backend\tests\test_governed_capability_foundation.py') -Force
foreach($relative in @('workspaces\palwakf_government\workspace_manifest.json','evidence\ledger\ledger_contract.json','evidence\ledger\entries.jsonl','config\controlled_first_prompt_pilot_v1.json')){$source=Join-Path $PackageRoot $relative;$target=Join-Path $ProjectRoot $relative;New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null;Copy-Item -LiteralPath $source -Destination $target -Force}
$appPath=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appText=Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
$importAnchor='from .local_agent_core import mount_local_agent_core'
$mountAnchor='mount_local_agent_core(app, project_root=PROJECT_ROOT)'
if($appText -notmatch [regex]::Escape($importAnchor)){throw 'APP_LOCAL_AGENT_CORE_IMPORT_ANCHOR_MISSING'}
if($appText -notmatch [regex]::Escape($mountAnchor)){throw 'APP_LOCAL_AGENT_CORE_MOUNT_ANCHOR_MISSING'}
$appText=$appText.Replace($importAnchor,($importAnchor+[Environment]::NewLine+'from .governed_capability_foundation import mount_governed_capability_foundation'))
$appText=$appText.Replace($mountAnchor,($mountAnchor+[Environment]::NewLine+'mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'))
[System.IO.File]::WriteAllText($appPath,$appText,(New-Object System.Text.UTF8Encoding($false)))
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'PYTHON_NOT_FOUND'}
$env:PYTHONDONTWRITEBYTECODE='1'
$bootstrap=@'
from pathlib import Path
import sys
root=Path(sys.argv[1])
sys.path.insert(0,str(root/'backend'/'src'))
from palwakf_local_agents.governed_capability_foundation.store import GovernedCapabilityFoundationStore
store=GovernedCapabilityFoundationStore(root)
store.initialize_all()
print('FOUNDATION_DB_INITIALIZATION=PASS')
'@
$bootstrapPath=Join-Path $env:TEMP ("initialize_unified_governed_capability_foundation_{0}.py" -f $stamp)
[System.IO.File]::WriteAllText($bootstrapPath,$bootstrap,(New-Object System.Text.UTF8Encoding($false)))
try{& $python $bootstrapPath $ProjectRoot;if($LASTEXITCODE -ne 0){throw 'FOUNDATION_DB_INITIALIZATION_FAILED'}}finally{Remove-Item -LiteralPath $bootstrapPath -Force -ErrorAction SilentlyContinue}
$manifest=[ordered]@{backup_items=@($backupItems);target_mutation_scope='MB1_TO_MB5_AND_MB6_CONFIGURATION_ONLY';government_local_agent_core_sqlite='UNCHANGED';model_execution='NONE';pilot_execution='NOT_EXECUTED'}
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $backup 'backup_manifest.json') -Encoding UTF8
'POST_APPLY_GOVERNMENT_MANIFEST=PASS';'POST_APPLY_EVIDENCE_LEDGER=PASS';'POST_APPLY_WORKSPACE_FOUNDATION_DATABASES=PASS';'POST_APPLY_PILOT_CONFIGURATION=PASS';'POST_APPLY_APP_MOUNT=PASS';'INSTALL_STATUS=COMPLETE';("BACKUP_PATH={0}" -f $backup);'TARGET_MUTATION_SCOPE=MB1_TO_MB5_AND_MB6_CONFIGURATION_ONLY';'GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MUTATION=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE'
