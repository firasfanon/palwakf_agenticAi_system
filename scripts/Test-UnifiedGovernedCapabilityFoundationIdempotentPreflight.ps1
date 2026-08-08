param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference='Stop'

function Get-FileSha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-ExactFileGroupState {
  param(
    [string]$GroupName,
    [string[]]$RelativePaths,
    [hashtable]$ExpectedByPath,
    [string]$Root
  )
  $present=@(); $missing=@(); $mismatch=@()
  foreach($relative in $RelativePaths){
    $absolute=Join-Path $Root $relative.Replace('/','\')
    if(-not(Test-Path -LiteralPath $absolute -PathType Leaf)){
      $missing += $relative
      continue
    }
    $present += $relative
    $actual=Get-FileSha256 $absolute
    if($actual -ne $ExpectedByPath[$relative]){$mismatch += $relative}
  }
  if($present.Count -eq 0){
    return [pscustomobject]@{name=$GroupName;state='PREIMAGE_EXPECTED';present=@();missing=@($missing);mismatch=@()}
  }
  if($missing.Count -eq 0 -and $mismatch.Count -eq 0){
    return [pscustomobject]@{name=$GroupName;state='EXACT_POSTIMAGE_PRESENT';present=@($present);missing=@();mismatch=@()}
  }
  return [pscustomobject]@{name=$GroupName;state='DRIFT_DETECTED';present=@($present);missing=@($missing);mismatch=@($mismatch)}
}

function Get-LedgerState {
  param([string]$Root,[hashtable]$ExpectedByPath)
  $contractRelative='evidence/ledger/ledger_contract.json'
  $entriesRelative='evidence/ledger/entries.jsonl'
  $contractPath=Join-Path $Root $contractRelative.Replace('/','\')
  $entriesPath=Join-Path $Root $entriesRelative.Replace('/','\')
  $contractExists=Test-Path -LiteralPath $contractPath -PathType Leaf
  $entriesExists=Test-Path -LiteralPath $entriesPath -PathType Leaf
  if(-not $contractExists -and -not $entriesExists){
    return [pscustomobject]@{name='evidence_ledger';state='PREIMAGE_EXPECTED';detail='ledger_files_absent'}
  }
  if(-not $contractExists -or -not $entriesExists){
    return [pscustomobject]@{name='evidence_ledger';state='DRIFT_DETECTED';detail='ledger_files_partially_present'}
  }
  $contractHash=Get-FileSha256 $contractPath
  if($contractHash -ne $ExpectedByPath[$contractRelative]){
    return [pscustomobject]@{name='evidence_ledger';state='DRIFT_DETECTED';detail='ledger_contract_hash_mismatch'}
  }
  $entriesHash=Get-FileSha256 $entriesPath
  if($entriesHash -eq $ExpectedByPath[$entriesRelative]){
    return [pscustomobject]@{name='evidence_ledger';state='EXACT_POSTIMAGE_PRESENT';detail='seed_ledger_exact'}
  }
  try {
    $prior=$null
    $lineCount=0
    foreach($line in (Get-Content -LiteralPath $entriesPath -Encoding UTF8)){
      if([string]::IsNullOrWhiteSpace($line)){continue}
      $item=$line | ConvertFrom-Json
      if([string]::IsNullOrWhiteSpace([string]$item.event_hash)){throw 'event_hash_missing'}
      if(([string]$item.event_hash) -notmatch '^[A-Fa-f0-9]{64}$'){throw 'event_hash_invalid'}
      if($item.previous_hash -ne $prior){throw 'previous_hash_chain_invalid'}
      $prior=[string]$item.event_hash
      $lineCount++
    }
    if($lineCount -lt 1){throw 'ledger_not_seed_and_not_chained'}
    return [pscustomobject]@{name='evidence_ledger';state='EXACT_POSTIMAGE_VALIDATED';detail=("chained_entries={0}" -f $lineCount)}
  }
  catch {
    return [pscustomobject]@{name='evidence_ledger';state='DRIFT_DETECTED';detail=("ledger_validation_failed={0}" -f $_.Exception.Message)}
  }
}

function Get-AppMountState {
  param([string]$AppPath,[string]$AcceptedBaselineHash)
  $text=Get-Content -LiteralPath $AppPath -Raw -Encoding UTF8
  $baseImport='from .local_agent_core import mount_local_agent_core'
  $baseMount='mount_local_agent_core(app, project_root=PROJECT_ROOT)'
  $foundationImport='from .governed_capability_foundation import mount_governed_capability_foundation'
  $foundationMount='mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)'
  $counts=[ordered]@{
    base_import=([regex]::Matches($text,[regex]::Escape($baseImport))).Count
    base_mount=([regex]::Matches($text,[regex]::Escape($baseMount))).Count
    foundation_import=([regex]::Matches($text,[regex]::Escape($foundationImport))).Count
    foundation_mount=([regex]::Matches($text,[regex]::Escape($foundationMount))).Count
  }
  $hash=Get-FileSha256 $AppPath
  if($hash -eq $AcceptedBaselineHash -and $counts.base_import -eq 1 -and $counts.base_mount -eq 1 -and $counts.foundation_import -eq 0 -and $counts.foundation_mount -eq 0){
    return [pscustomobject]@{name='app_mount';state='PREIMAGE_EXPECTED';detail=$counts}
  }
  if($counts.base_import -eq 1 -and $counts.base_mount -eq 1 -and $counts.foundation_import -eq 1 -and $counts.foundation_mount -eq 1){
    return [pscustomobject]@{name='app_mount';state='STRUCTURAL_EXACT_POSTIMAGE_PRESENT';detail=$counts}
  }
  return [pscustomobject]@{name='app_mount';state='DRIFT_DETECTED';detail=$counts}
}

function Get-FoundationDatabaseState {
  param([string]$Root,[string]$PythonPath)
  $workspaces=@('personal_development','commercial_projects','research_learning')
  $paths=@($workspaces | ForEach-Object { Join-Path $Root ("workspaces\{0}\capability_foundation.sqlite" -f $_) })
  $present=@($paths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
  if($present.Count -eq 0){
    return [pscustomobject]@{name='foundation_databases';state='PREIMAGE_EXPECTED';detail='all_databases_absent'}
  }
  if($present.Count -ne $paths.Count){
    return [pscustomobject]@{name='foundation_databases';state='DRIFT_DETECTED';detail='databases_partially_present'}
  }
  $temp=Join-Path $env:TEMP ("gcf_db_state_{0}.py" -f (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
  $code=@'
import json, sqlite3, sys
from pathlib import Path
root=Path(sys.argv[1])
workspaces=("personal_development","commercial_projects","research_learning")
required={"schema_migrations","tasks","projects","review_records","tool_runs","audit_events"}
result=[]
for ws in workspaces:
    path=root/"workspaces"/ws/"capability_foundation.sqlite"
    con=sqlite3.connect(path)
    tables={row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    version=con.execute("select count(*) from schema_migrations where version='GOVERNED_CAPABILITY_FOUNDATION_V1'").fetchone()[0] if "schema_migrations" in tables else 0
    bound=con.execute("select count(*) from audit_events where event_type='WORKSPACE_CAPABILITY_FOUNDATION_BOUND'").fetchone()[0] if "audit_events" in tables else 0
    con.close()
    result.append({"workspace_id":ws,"valid":required.issubset(tables) and version==1 and bound>=1})
print(json.dumps(result))
'@
  [System.IO.File]::WriteAllText($temp,$code,(New-Object System.Text.UTF8Encoding($false)))
  try{
    $raw=& $PythonPath $temp $Root
    if($LASTEXITCODE -ne 0){throw 'sqlite_validation_process_failed'}
    $result=$raw | ConvertFrom-Json
    if(@($result | Where-Object { -not $_.valid }).Count -eq 0){
      return [pscustomobject]@{name='foundation_databases';state='EXACT_POSTIMAGE_VALIDATED';detail='all_schemas_and_binding_events_valid'}
    }
    return [pscustomobject]@{name='foundation_databases';state='DRIFT_DETECTED';detail='database_schema_or_binding_validation_failed'}
  }
  catch{
    return [pscustomobject]@{name='foundation_databases';state='DRIFT_DETECTED';detail=("database_validation_error={0}" -f $_.Exception.Message)}
  }
  finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
}

$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$baselinePath=Join-Path $PackageRoot 'contracts\accepted_baseline_hashes_v1.json'
$postimagePath=Join-Path $PackageRoot 'contracts\expected_postimage_hashes_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$baseline=Get-Content -LiteralPath $baselinePath -Raw -Encoding UTF8 | ConvertFrom-Json
$postimage=Get-Content -LiteralPath $postimagePath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures=New-Object 'System.Collections.Generic.List[string]'
$expectedByPath=@{}
foreach($entry in $postimage.files){$expectedByPath[[string]$entry.path]=[string]$entry.sha256}
$baselineRows=@()
$appBaselineProperty=@($baseline.files.psobject.Properties | Where-Object { $_.Name.Replace('\','/') -eq 'backend/src/palwakf_local_agents/app.py' } | Select-Object -First 1)
if($appBaselineProperty.Count -ne 1){throw 'ACCEPTED_BASELINE_APP_HASH_NOT_FOUND'}
$acceptedAppHash=[string]$appBaselineProperty.Value
foreach($property in $baseline.files.psobject.Properties){
  $relative=[string]$property.Name
  $absolute=Join-Path $ProjectRoot $relative.Replace('/','\')
  if(-not(Test-Path -LiteralPath $absolute -PathType Leaf)){
    $baselineRows += [pscustomobject]@{RelativePath=$relative;State='BASELINE_FILE_MISSING';ActualHash=$null}
    $failures.Add(("BASELINE_FILE_MISSING={0}" -f $relative))
    continue
  }
  if($relative.Replace('\','/') -eq 'backend/src/palwakf_local_agents/app.py'){continue}
  $actual=Get-FileSha256 $absolute
  $state=if($actual -eq [string]$property.Value){'TARGET_EQUALS_ACCEPTED_BASELINE'}else{'TARGET_HASH_MISMATCH'}
  $baselineRows += [pscustomobject]@{RelativePath=$relative;State=$state;ActualHash=$actual}
  if($state -ne 'TARGET_EQUALS_ACCEPTED_BASELINE'){$failures.Add(("BASELINE_HASH_MISMATCH={0}" -f $relative))}
}
$appPath=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appState=Get-AppMountState -AppPath $appPath -AcceptedBaselineHash $acceptedAppHash
$baselineRows += [pscustomobject]@{RelativePath='backend/src/palwakf_local_agents/app.py';State=$appState.state;ActualHash=(Get-FileSha256 $appPath)}
if($appState.state -eq 'DRIFT_DETECTED'){$failures.Add('APP_MOUNT_STATE_DRIFT_DETECTED')}

$governmentManifestState=Get-ExactFileGroupState -GroupName 'government_manifest' -RelativePaths @('workspaces/palwakf_government/workspace_manifest.json') -ExpectedByPath $expectedByPath -Root $ProjectRoot
$sourceState=Get-ExactFileGroupState -GroupName 'governed_capability_source_and_test' -RelativePaths @($postimage.groups.governed_capability_source_and_test) -ExpectedByPath $expectedByPath -Root $ProjectRoot
$pilotState=Get-ExactFileGroupState -GroupName 'pilot_config' -RelativePaths @('config/controlled_first_prompt_pilot_v1.json') -ExpectedByPath $expectedByPath -Root $ProjectRoot
$ledgerState=Get-LedgerState -Root $ProjectRoot -ExpectedByPath $expectedByPath
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){$failures.Add('PYTHON_NOT_FOUND')}
$databaseState=if(Test-Path -LiteralPath $python -PathType Leaf){Get-FoundationDatabaseState -Root $ProjectRoot -PythonPath $python}else{[pscustomobject]@{name='foundation_databases';state='DRIFT_DETECTED';detail='python_missing'}}
foreach($component in @($governmentManifestState,$sourceState,$pilotState,$ledgerState,$databaseState)){
  if($component.state -eq 'DRIFT_DETECTED'){$failures.Add(("COMPONENT_DRIFT_DETECTED={0}" -f $component.name))}
}
$governmentDb=Join-Path $ProjectRoot 'workspaces\palwakf_government\local_agent_core.sqlite'
$governmentSqliteState=if(Test-Path -LiteralPath $governmentDb -PathType Leaf){'PRESENT'}else{'MISSING'}
if($governmentSqliteState -ne 'PRESENT'){$failures.Add('GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MISSING')}
foreach($workspaceId in @('personal_development','commercial_projects','research_learning')){
  $workspaceManifest=Join-Path $ProjectRoot ("workspaces\{0}\workspace_manifest.json" -f $workspaceId)
  if(-not(Test-Path -LiteralPath $workspaceManifest -PathType Leaf)){$failures.Add(("WORKSPACE_MANIFEST_MISSING={0}" -f $workspaceId))}
}
$states=[ordered]@{
  government_manifest=$governmentManifestState
  governed_capability_source_and_test=$sourceState
  pilot_config=$pilotState
  evidence_ledger=$ledgerState
  foundation_databases=$databaseState
  app_mount=$appState
}
$scriptHash=Get-FileSha256 $PSCommandPath
$outDir=Join-Path $env:TEMP ("unified_governed_capability_idempotent_preflight_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$manifest=[ordered]@{
  manifest_binding_schema_version='2'
  package_id=$contract.package_id
  contract_sha256=(Get-FileSha256 $contractPath)
  preflight_script_sha256=$scriptHash
  project_root=(Resolve-Path -LiteralPath $ProjectRoot).Path
  generated_at=(Get-Date).ToString('o')
  failure_count=$failures.Count
  failures=@($failures)
  government_sqlite_state=$governmentSqliteState
  component_states=$states
  baseline_rows=@($baselineRows)
}
$manifestPath=Join-Path $outDir 'preflight_manifest.json'
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
'===== UNIFIED GOVERNED CAPABILITY FOUNDATION IDEMPOTENT PREFLIGHT ====='
$baselineRows | Format-Table -AutoSize
foreach($name in $states.Keys){("COMPONENT_STATE_{0}={1}" -f $name.ToUpperInvariant(),$states[$name].state)}
("GOVERNMENT_SQLITE_STATE={0}" -f $governmentSqliteState)
("PREFLIGHT_MANIFEST={0}" -f $manifestPath)
("PREFLIGHT_FAILURE_COUNT={0}" -f $failures.Count)
'PREFLIGHT_RECONCILIATION_MODE=IDEMPOTENT_EXACT_POSTIMAGE_AWARE'
'PROJECT_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
if($failures.Count -gt 0){
  ('PREFLIGHT_FAILURES=' + ($failures -join ';'))
  throw 'PREFLIGHT_RESULT_FAIL'
}
'PREFLIGHT_RESULT=PASS'
