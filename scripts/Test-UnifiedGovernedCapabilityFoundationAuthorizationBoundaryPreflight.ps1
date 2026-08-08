param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$statePath=Join-Path $PackageRoot 'contracts\authorization_boundary_reconciliation_state_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8|ConvertFrom-Json
$state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json
$failures=New-Object 'System.Collections.Generic.List[string]'
$components=[ordered]@{}
function Get-State([string]$relative,[string]$legacyHash,[string]$postHash,[bool]$allowAbsent){
  $target=Join-Path $ProjectRoot $relative
  if(-not(Test-Path -LiteralPath $target -PathType Leaf)){return $(if($allowAbsent){'PREIMAGE_EXPECTED'}else{'MISSING_REQUIRED'})}
  $actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if($postHash -and $actual -eq $postHash){return 'EXACT_POSTIMAGE_PRESENT'}
  if($legacyHash -and $actual -eq $legacyHash){return 'LEGACY_RECONCILIATION_PREIMAGE'}
  return 'DRIFT_DETECTED'
}
foreach($p in $state.postimage_hashes.psobject.Properties){
  $relative=$p.Name;$post=[string]$p.Value;$legacy=$null
  $legacyProp=$state.legacy_preimage_hashes.psobject.Properties[$relative]
  if($legacyProp){$legacy=[string]$legacyProp.Value}
  $allowAbsent=@($state.new_preimage_absent) -contains $relative
  $components[$relative]=Get-State $relative $legacy $post $allowAbsent
  if($components[$relative] -in @('MISSING_REQUIRED','DRIFT_DETECTED')){$failures.Add(('SOURCE_STATE_INVALID={0}:{1}' -f $relative,$components[$relative]))}
}
$appPath=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
if(-not(Test-Path -LiteralPath $appPath -PathType Leaf)){$failures.Add('APP_FILE_MISSING')}else{
  $appHash=(Get-FileHash -LiteralPath $appPath -Algorithm SHA256).Hash
  $appText=Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
  $newImport='from .governed_capability_foundation import mount_governed_capability_foundation'
  $newMount='mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'
  if($appHash -eq $state.app_preimage_sha256 -and $appText -notmatch [regex]::Escape($newImport) -and $appText -notmatch [regex]::Escape($newMount)){$components['app_mount']='PREIMAGE_EXPECTED'}
  elseif($appText -match [regex]::Escape($newImport) -and $appText -match [regex]::Escape($newMount)){$components['app_mount']='STRUCTURAL_EXACT_POSTIMAGE_PRESENT'}
  else{$components['app_mount']='DRIFT_DETECTED';$failures.Add('APP_MOUNT_STATE_INVALID')}
}
foreach($relative in @('config\controlled_first_prompt_pilot_v1.json','workspaces\palwakf_government\workspace_manifest.json')){
  $hash=[string]$state.unchanged_exact_hashes.psobject.Properties[$relative].Value
  $target=Join-Path $ProjectRoot $relative
  if(-not(Test-Path -LiteralPath $target -PathType Leaf)){$components[$relative]='MISSING_REQUIRED';$failures.Add(('UNCHANGED_COMPONENT_MISSING={0}' -f $relative))}
  elseif((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $hash){$components[$relative]='EXACT_POSTIMAGE_PRESENT'}
  else{$components[$relative]='DRIFT_DETECTED';$failures.Add(('UNCHANGED_COMPONENT_DRIFT={0}' -f $relative))}
}
$ledger=Join-Path $ProjectRoot 'evidence\ledger\entries.jsonl'
if(Test-Path -LiteralPath $ledger -PathType Leaf){$components['evidence_entries']='PRESERVE_APPEND_ONLY'}else{$components['evidence_entries']='PREIMAGE_EXPECTED'}
$foundationStates=@{}
foreach($workspaceId in @('personal_development','commercial_projects','research_learning')){
  $db=Join-Path $ProjectRoot ('workspaces\{0}\capability_foundation.sqlite' -f $workspaceId)
  $foundationStates[$workspaceId]=if(Test-Path -LiteralPath $db -PathType Leaf){'STRUCTURAL_EXISTING_REQUIRES_POST_APPLY_SCHEMA_VERIFY'}else{'PREIMAGE_EXPECTED'}
}
$governmentDb=Join-Path $ProjectRoot 'workspaces\palwakf_government\local_agent_core.sqlite'
if(-not(Test-Path -LiteralPath $governmentDb -PathType Leaf)){$failures.Add('GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MISSING')}
$scriptHash=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
$outDir=Join-Path $env:TEMP ('unified_gcf_authz_preflight_{0}' -f (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
New-Item -ItemType Directory -Path $outDir -Force|Out-Null
$manifest=[ordered]@{package_id=$contract.package_id;contract_sha256=(Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash;preflight_script_sha256=$scriptHash;project_root=(Resolve-Path -LiteralPath $ProjectRoot).Path;generated_at=(Get-Date).ToString('o');failure_count=$failures.Count;failures=@($failures);component_states=$components;foundation_database_states=$foundationStates;government_sqlite_state='PRESENT'}
$manifestPath=Join-Path $outDir 'preflight_manifest.json'
$manifest|ConvertTo-Json -Depth 20|Set-Content -LiteralPath $manifestPath -Encoding UTF8
'===== AUTHORIZATION BOUNDARY AND EXECUTION CARRIER PREFLIGHT ====='
foreach($key in $components.Keys){('COMPONENT_STATE_{0}={1}' -f ($key -replace '[^A-Za-z0-9]','_').ToUpper(),$components[$key])}
foreach($key in $foundationStates.Keys){('FOUNDATION_DATABASE_STATE_{0}={1}' -f $key.ToUpper(),$foundationStates[$key])}
'GOVERNMENT_SQLITE_STATE=PRESENT';('PREFLIGHT_MANIFEST={0}' -f $manifestPath);('PREFLIGHT_FAILURE_COUNT={0}' -f $failures.Count)
'PREFLIGHT_AUTHORIZATION_BOUNDARY=ACTOR_SCOPE_AND_CLIENT_SCOPE_REQUIRED';'PROJECT_MUTATION=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'EXTERNAL_NETWORK=NONE'
if($failures.Count -gt 0){'PREFLIGHT_RESULT=FAIL';'PREFLIGHT_FAILURES='+($failures -join ';');throw 'AUTHORIZATION_BOUNDARY_PREFLIGHT_FAILED'}
'PREFLIGHT_RESULT=PASS'
