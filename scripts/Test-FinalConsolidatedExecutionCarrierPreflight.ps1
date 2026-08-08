param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$contractPath = Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$statePath = Join-Path $PackageRoot 'contracts\final_execution_carrier_reconciliation_state_v1.json'
$contract = Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = New-Object 'System.Collections.Generic.List[string]'
$states = [ordered]@{}

function Get-PropertyValue {
  param([Parameter(Mandatory=$true)]$Object,[Parameter(Mandatory=$true)][string]$Name)
  $property = $Object.PSObject.Properties[$Name]
  if($null -eq $property){ return $null }
  return [string]$property.Value
}
function Get-FileState {
  param([string]$RelativePath,[string]$ExpectedHash,[string]$LegacyHash,[bool]$AllowAbsent)
  $target = Join-Path $ProjectRoot $RelativePath
  if(-not (Test-Path -LiteralPath $target -PathType Leaf)){
    if($AllowAbsent){ return 'PREIMAGE_EXPECTED' }
    return 'MISSING_REQUIRED'
  }
  $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if($actual -eq $ExpectedHash){ return 'EXACT_POSTIMAGE_PRESENT' }
  if($LegacyHash -and $actual -eq $LegacyHash){ return 'LEGACY_PREIMAGE_ACCEPTED' }
  return 'DRIFT_DETECTED'
}

foreach($property in $state.source_postimage_hashes.PSObject.Properties){
  $relative = $property.Name
  $expectedHash = [string]$property.Value
  $legacyHash = Get-PropertyValue -Object $state.legacy_preimage_hashes -Name $relative
  $allowAbsent = @($state.preimage_absent_allowed) -contains $relative
  $componentState = Get-FileState -RelativePath $relative -ExpectedHash $expectedHash -LegacyHash $legacyHash -AllowAbsent $allowAbsent
  $states[$relative] = $componentState
  if($componentState -in @('MISSING_REQUIRED','DRIFT_DETECTED')){ $failures.Add(('SOURCE_STATE_INVALID={0}|{1}' -f $relative,$componentState)) }
}

foreach($definition in @(
  @{ Relative='config\controlled_first_prompt_pilot_v1.json'; Expected=[string]$state.pilot_config_sha256 },
  @{ Relative='workspaces\palwakf_government\workspace_manifest.json'; Expected=[string]$state.government_manifest_sha256 }
)){
  $allowAbsent = @($state.preimage_absent_allowed) -contains $definition.Relative
  $componentState = Get-FileState -RelativePath $definition.Relative -ExpectedHash $definition.Expected -LegacyHash $null -AllowAbsent $allowAbsent
  $states[$definition.Relative] = $componentState
  if($componentState -in @('MISSING_REQUIRED','DRIFT_DETECTED')){ $failures.Add(('CONTROLLED_COMPONENT_STATE_INVALID={0}|{1}' -f $definition.Relative,$componentState)) }
}

$appPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appImport = 'from .governed_capability_foundation import mount_governed_capability_foundation'
$appMount = 'mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'
if(-not (Test-Path -LiteralPath $appPath -PathType Leaf)){
  $states['app_mount'] = 'MISSING_REQUIRED'
  $failures.Add('APP_FILE_MISSING')
}
else {
  $appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
  $appHash = (Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash
  if($appHash -eq [string]$state.app_preimage_sha256 -and $appText -notmatch [regex]::Escape($appImport) -and $appText -notmatch [regex]::Escape($appMount)){
    $states['app_mount'] = 'PREIMAGE_EXPECTED'
  }
  elseif($appText -match [regex]::Escape($appImport) -and $appText -match [regex]::Escape($appMount)){
    $states['app_mount'] = 'STRUCTURAL_EXACT_POSTIMAGE_PRESENT'
  }
  else {
    $states['app_mount'] = 'DRIFT_DETECTED'
    $failures.Add('APP_MOUNT_STATE_INVALID')
  }
}

$foundationStates = [ordered]@{}
foreach($workspaceId in @('personal_development','commercial_projects','research_learning')){
  $path = Join-Path $ProjectRoot ('workspaces\{0}\capability_foundation.sqlite' -f $workspaceId)
  if(Test-Path -LiteralPath $path -PathType Leaf){ $foundationStates[$workspaceId] = 'STRUCTURAL_EXISTING_REQUIRES_POST_APPLY_SCHEMA_VERIFY' }
  else { $foundationStates[$workspaceId] = 'PREIMAGE_EXPECTED' }
}
$governmentDb = Join-Path $ProjectRoot 'workspaces\palwakf_government\local_agent_core.sqlite'
$governmentDbState = if(Test-Path -LiteralPath $governmentDb -PathType Leaf){ 'PRESENT' }else{ 'MISSING_REQUIRED' }
if($governmentDbState -ne 'PRESENT'){ $failures.Add('GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MISSING') }
$ledgerEntries = Join-Path $ProjectRoot 'evidence\ledger\entries.jsonl'
$states['evidence_entries'] = if(Test-Path -LiteralPath $ledgerEntries -PathType Leaf){ 'PRESERVE_APPEND_ONLY' }else{ 'PREIMAGE_EXPECTED' }

$outDir = Join-Path $env:TEMP ('final_consolidated_execution_carrier_preflight_{0}' -f (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$manifest = [pscustomobject]@{
  package_id = $contract.package_id
  contract_sha256 = (Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
  state_contract_sha256 = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash
  preflight_script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
  project_root = (Resolve-Path -LiteralPath $ProjectRoot).Path
  generated_at = (Get-Date).ToString('o')
  failure_count = $failures.Count
  failures = @($failures)
  component_states = [pscustomobject]$states
  foundation_database_states = [pscustomobject]$foundationStates
  government_sqlite_state = $governmentDbState
}
$manifestPath = Join-Path $outDir 'preflight_manifest.json'
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
'===== FINAL CONSOLIDATED EXECUTION CARRIER PREFLIGHT ====='
foreach($key in $states.Keys){ ('COMPONENT_STATE_{0}={1}' -f ($key -replace '[^A-Za-z0-9]','_').ToUpper(),$states[$key]) }
foreach($key in $foundationStates.Keys){ ('FOUNDATION_DATABASE_STATE_{0}={1}' -f $key.ToUpper(),$foundationStates[$key]) }
('GOVERNMENT_SQLITE_STATE={0}' -f $governmentDbState)
('PREFLIGHT_MANIFEST={0}' -f $manifestPath)
('PREFLIGHT_FAILURE_COUNT={0}' -f $failures.Count)
'PREFLIGHT_RECONCILIATION_MODE=IDEMPOTENT_EXACT_POSTIMAGE_AWARE'
'PREFLIGHT_AUTHORIZATION_BOUNDARY=ACTOR_SCOPE_AND_CLIENT_SCOPE_REQUIRED'
'PROJECT_MUTATION=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'EXTERNAL_NETWORK=NONE'
if($failures.Count -gt 0){
  'PREFLIGHT_RESULT=FAIL'
  'PREFLIGHT_FAILURES='+($failures -join ';')
  throw 'FINAL_CONSOLIDATED_EXECUTION_CARRIER_PREFLIGHT_FAILED'
}
'PREFLIGHT_RESULT=PASS'
