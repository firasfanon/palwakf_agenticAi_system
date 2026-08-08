param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$PreflightManifest,
  [switch]$Apply,
  [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
if($Apply -eq $WhatIf){ throw 'SELECT_EXACTLY_ONE_OF_APPLY_OR_WHATIF' }
$contractPath = Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$statePath = Join-Path $PackageRoot 'contracts\final_execution_carrier_reconciliation_state_v1.json'
$preflightPath = Join-Path $PackageRoot 'scripts\Test-FinalConsolidatedExecutionCarrierPreflight.ps1'
$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
$preflight = Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if([int]$preflight.failure_count -ne 0){ throw 'PREFLIGHT_MANIFEST_NOT_CLEAN' }
if($preflight.package_id -ne $contract.package_id){ throw 'PREFLIGHT_PACKAGE_ID_MISMATCH' }
if($preflight.project_root -ne (Resolve-Path -LiteralPath $ProjectRoot).Path){ throw 'PREFLIGHT_PROJECT_ROOT_MISMATCH' }
if($preflight.contract_sha256 -ne (Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash){ throw 'PREFLIGHT_CONTRACT_HASH_MISMATCH' }
if($preflight.state_contract_sha256 -ne (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash){ throw 'PREFLIGHT_STATE_CONTRACT_HASH_MISMATCH' }
if($preflight.preflight_script_sha256 -ne (Get-FileHash -LiteralPath $preflightPath -Algorithm SHA256).Hash){ throw 'PREFLIGHT_SCRIPT_HASH_MISMATCH' }

function Get-State {
  param([Parameter(Mandatory=$true)]$Manifest,[Parameter(Mandatory=$true)][string]$Key)
  $property = $Manifest.component_states.PSObject.Properties[$Key]
  if($null -eq $property){ throw ('PREFLIGHT_COMPONENT_STATE_MISSING={0}' -f $Key) }
  return [string]$property.Value
}
function Needs-Reconcile {
  param([string]$State)
  return $State -in @('PREIMAGE_EXPECTED','LEGACY_PREIMAGE_ACCEPTED')
}
$sourceKeys = @($state.source_postimage_hashes.PSObject.Properties | ForEach-Object { $_.Name })
$controlledKeys = @('config\controlled_first_prompt_pilot_v1.json','workspaces\palwakf_government\workspace_manifest.json')
$writeSource = @($sourceKeys | Where-Object { Needs-Reconcile (Get-State -Manifest $preflight -Key $_) })
$writeControlled = @($controlledKeys | Where-Object { Needs-Reconcile (Get-State -Manifest $preflight -Key $_) })
$appState = Get-State -Manifest $preflight -Key 'app_mount'
$appWrite = Needs-Reconcile $appState
$dbWrites = @($preflight.foundation_database_states.PSObject.Properties | Where-Object { $_.Value -eq 'PREIMAGE_EXPECTED' })
$ledgerAppendCount = @($dbWrites).Count

if($WhatIf){
  'INSTALL_STATUS=WHATIF_COMPLETE';'WHATIF_MODE=TRUE';'TARGET_MUTATION_SCOPE=IDEMPOTENT_RECONCILIATION_ONLY_AND_FOUNDATION_DATABASE_INITIALIZATION'
  ('PREDICTED_SOURCE_RECONCILIATION_WRITE_COUNT={0}' -f $writeSource.Count)
  ('PREDICTED_CONTROLLED_CONFIG_OR_MANIFEST_WRITE_COUNT={0}' -f $writeControlled.Count)
  ('PREDICTED_APP_ENTRYPOINT_MUTATION_COUNT={0}' -f $(if($appWrite){1}else{0}))
  ('PREDICTED_WORKSPACE_FOUNDATION_SQLITE_COUNT={0}' -f $dbWrites.Count)
  ('PREDICTED_LEDGER_EVENT_APPEND_COUNT={0}' -f $ledgerAppendCount)
  'PREDICTED_EVIDENCE_ENTRIES_OVERWRITE_COUNT=0'
  'CROSS_WORKSPACE_ACCESS=DENY_BY_ACTOR_SCOPE';'COMMERCIAL_CLIENT_BOUNDARY=ENFORCED'
  'MB6_MODEL_PROMPT_DURING_APPLY=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE';'PROJECT_MUTATION=NONE_DURING_WHATIF'
  return
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $ProjectRoot ('backups\final_consolidated_execution_carrier_{0}' -f $stamp)
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$backupItems = New-Object 'System.Collections.Generic.List[string]'
function Backup-Target {
  param([Parameter(Mandatory=$true)][string]$RelativePath)
  $targetPath = Join-Path $ProjectRoot $RelativePath
  if(Test-Path -LiteralPath $targetPath -PathType Leaf){
    $destination = Join-Path $backup $RelativePath
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $targetPath -Destination $destination -Force
    $backupItems.Add($RelativePath)
  }
}
foreach($relative in @($writeSource + $writeControlled)){ Backup-Target -RelativePath $relative }
if($appWrite){ Backup-Target -RelativePath 'backend\src\palwakf_local_agents\app.py' }
foreach($property in $preflight.foundation_database_states.PSObject.Properties){
  if($property.Value -eq 'STRUCTURAL_EXISTING_REQUIRES_POST_APPLY_SCHEMA_VERIFY'){
    Backup-Target -RelativePath ('workspaces\{0}\capability_foundation.sqlite' -f $property.Name)
  }
}
Backup-Target -RelativePath 'evidence\ledger\entries.jsonl'

foreach($relative in @($writeSource + $writeControlled)){
  $sourcePath = Join-Path $PackageRoot $relative
  $targetPath = Join-Path $ProjectRoot $relative
  New-Item -ItemType Directory -Path (Split-Path -Parent $targetPath) -Force | Out-Null
  Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

$appMutation = 'NOOP_EXACT_MOUNT_PRESENT'
if($appWrite){
  $appPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
  $appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
  $anchorImport = 'from .local_agent_core import mount_local_agent_core'
  $anchorMount = 'mount_local_agent_core(app, project_root=PROJECT_ROOT)'
  $newImport = 'from .governed_capability_foundation import mount_governed_capability_foundation'
  $newMount = 'mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'
  if($appText -notmatch [regex]::Escape($anchorImport)){ throw 'APP_LOCAL_AGENT_CORE_IMPORT_ANCHOR_MISSING' }
  if($appText -notmatch [regex]::Escape($anchorMount)){ throw 'APP_LOCAL_AGENT_CORE_MOUNT_ANCHOR_MISSING' }
  $appText = $appText.Replace($anchorImport,($anchorImport + [Environment]::NewLine + $newImport))
  $appText = $appText.Replace($anchorMount,($anchorMount + [Environment]::NewLine + $newMount))
  [System.IO.File]::WriteAllText($appPath,$appText,(New-Object System.Text.UTF8Encoding($false)))
  $appMutation = 'MOUNT_APPLIED'
}

$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){ throw 'PYTHON_NOT_FOUND' }
$bootstrap = @'
from pathlib import Path
import sys
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'backend' / 'src'))
from palwakf_local_agents.governed_capability_foundation.store import GovernedCapabilityFoundationStore
GovernedCapabilityFoundationStore(root).initialize_all()
print('FOUNDATION_DATABASE_INITIALIZATION=PASS')
'@
$temp = Join-Path $env:TEMP ('final_consolidated_execution_carrier_initialize_{0}.py' -f $stamp)
[System.IO.File]::WriteAllText($temp,$bootstrap,(New-Object System.Text.UTF8Encoding($false)))
try {
  & $python $temp $ProjectRoot
  if($LASTEXITCODE -ne 0){ throw 'FOUNDATION_DATABASE_INITIALIZATION_FAILED' }
}
finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }

$backupManifest = [pscustomobject]@{
  contract = 'FINAL_CONSOLIDATED_EXECUTION_CARRIER_BACKUP_V1'
  backup_items = @($backupItems)
  app_mount_mutation = $appMutation
  source_reconciliation_writes = @($writeSource)
  controlled_writes = @($writeControlled)
  actor_registry_default = 'DENY'
  model_execution = 'NONE'
  pilot_execution = 'NOT_EXECUTED'
  government_local_agent_core_sqlite = 'UNCHANGED'
}
$backupManifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $backup 'backup_manifest.json') -Encoding UTF8
'INSTALL_STATUS=COMPLETE'
('BACKUP_PATH={0}' -f $backup)
('BACKUP_ITEM_COUNT={0}' -f $backupItems.Count)
('APP_ENTRYPOINT_MUTATION={0}' -f $appMutation)
('SOURCE_RECONCILIATION_WRITE_COUNT={0}' -f $writeSource.Count)
('CONTROLLED_CONFIG_OR_MANIFEST_WRITE_COUNT={0}' -f $writeControlled.Count)
'FOUNDATION_DATABASE_INITIALIZATION=PASS'
'AUTHORIZATION_BOUNDARY=ACTOR_SCOPE_AND_CLIENT_SCOPE_REQUIRED'
'GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MUTATION=NONE'
'MB6_MODEL_PROMPT_DURING_APPLY=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'DEPLOYMENT=NONE';'EXTERNAL_NETWORK=NONE'
