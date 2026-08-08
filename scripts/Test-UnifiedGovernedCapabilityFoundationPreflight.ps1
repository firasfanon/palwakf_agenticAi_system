param([Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$baselinePath=Join-Path $PackageRoot 'contracts\accepted_baseline_hashes_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$baseline=Get-Content -LiteralPath $baselinePath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures=New-Object 'System.Collections.Generic.List[string]'
$rows=@()
foreach($property in $baseline.files.psobject.Properties){$relative=$property.Name;$expected=[string]$property.Value;$absolute=Join-Path $ProjectRoot $relative;if(-not(Test-Path -LiteralPath $absolute -PathType Leaf)){$failures.Add("BASELINE_FILE_MISSING=$relative");continue};$actual=(Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash;$state=if($actual -eq $expected){'TARGET_EQUALS_ACCEPTED_BASELINE'}else{'TARGET_HASH_MISMATCH'};$rows += [pscustomobject]@{RelativePath=$relative;State=$state;ActualHash=$actual};if($state -ne 'TARGET_EQUALS_ACCEPTED_BASELINE'){$failures.Add("BASELINE_HASH_MISMATCH=$relative")}}
$appPath=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$appText=Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
if($appText -match [regex]::Escape('from .governed_capability_foundation import mount_governed_capability_foundation')){$failures.Add('CAPABILITY_FOUNDATION_ALREADY_MOUNTED_IMPORT')}
if($appText -match [regex]::Escape('mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)')){$failures.Add('CAPABILITY_FOUNDATION_ALREADY_MOUNTED_CALL')}
$governmentManifest=Join-Path $ProjectRoot 'workspaces\palwakf_government\workspace_manifest.json'
$governmentDb=Join-Path $ProjectRoot 'workspaces\palwakf_government\local_agent_core.sqlite'
$govManifestState=if(Test-Path -LiteralPath $governmentManifest){'PRESENT_RECONCILIATION_REAPPLY'}else{'MISSING_EXPECTED_P0_PREIMAGE'}
if(-not(Test-Path -LiteralPath $governmentDb -PathType Leaf)){$failures.Add('GOVERNMENT_LOCAL_AGENT_CORE_SQLITE_MISSING')}
foreach($workspaceId in @('personal_development','commercial_projects','research_learning')){
  $manifest=Join-Path $ProjectRoot ("workspaces\\{0}\\workspace_manifest.json" -f $workspaceId)
  $db=Join-Path $ProjectRoot ("workspaces\\{0}\\capability_foundation.sqlite" -f $workspaceId)
  if(-not(Test-Path -LiteralPath $manifest -PathType Leaf)){$failures.Add(("WORKSPACE_MANIFEST_MISSING={0}" -f $workspaceId))}
  if(Test-Path -LiteralPath $db -PathType Leaf){$failures.Add(("FOUNDATION_DB_ALREADY_PRESENT={0}" -f $workspaceId))}
}
$sourceRoot=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_capability_foundation'
if(Test-Path -LiteralPath $sourceRoot){$failures.Add('GOVERNED_CAPABILITY_FOUNDATION_SOURCE_ALREADY_PRESENT')}
$pilotConfig=Join-Path $ProjectRoot 'config\controlled_first_prompt_pilot_v1.json'
if(Test-Path -LiteralPath $pilotConfig){$failures.Add('CONTROLLED_PILOT_CONFIG_ALREADY_PRESENT')}
$ledgerRoot=Join-Path $ProjectRoot 'evidence\ledger'
if(Test-Path -LiteralPath $ledgerRoot){$failures.Add('EVIDENCE_LEDGER_ALREADY_PRESENT')}
$scriptHash=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
$manifest=[ordered]@{package_id=$contract.package_id;contract_sha256=(Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash;preflight_script_sha256=$scriptHash;project_root=(Resolve-Path -LiteralPath $ProjectRoot).Path;generated_at=(Get-Date).ToString('o');failure_count=$failures.Count;failures=@($failures);government_manifest_state=$govManifestState;government_sqlite_state='PRESENT';baseline_rows=@($rows)}
$outDir=Join-Path $env:TEMP ("unified_governed_capability_preflight_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$manifestPath=Join-Path $outDir 'preflight_manifest.json'
$manifest | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$rows | Format-Table -AutoSize
("GOVERNMENT_MANIFEST_STATE={0}" -f $govManifestState)
'GOVERNMENT_SQLITE_STATE=PRESENT'
("PREFLIGHT_MANIFEST={0}" -f $manifestPath)
("PREFLIGHT_FAILURE_COUNT={0}" -f $failures.Count)
'PROJECT_MUTATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
if($failures.Count -gt 0){('PREFLIGHT_FAILURES=' + ($failures -join ';'));throw 'PREFLIGHT_RESULT_FAIL'}
'PREFLIGHT_RESULT=PASS'
