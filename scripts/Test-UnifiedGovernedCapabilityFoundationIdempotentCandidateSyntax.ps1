param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
 'contracts\accepted_baseline_hashes_v1.json',
 'contracts\master_batch_contract_v1.json',
 'contracts\expected_postimage_hashes_v1.json',
 'scripts\Test-UnifiedGovernedCapabilityFoundationIdempotentCandidateSyntax.ps1',
 'scripts\Test-UnifiedGovernedCapabilityFoundationIdempotentPreflight.ps1',
 'scripts\Install-UnifiedGovernedCapabilityFoundationIdempotentReconciliationV1.ps1',
 'scripts\Invoke-UnifiedGovernedCapabilityFoundationIdempotentReadiness.ps1'
)
$missing=@()
foreach($relative in $required){if(-not(Test-Path -LiteralPath (Join-Path $PackageRoot $relative))){$missing += $relative}}
$inventoryValid=$true
try{
  $inventory=Get-Content -LiteralPath (Join-Path $PackageRoot 'PACKAGE_INVENTORY.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach($entry in $inventory.files){
    $path=Join-Path $PackageRoot ([string]$entry.path).Replace('/','\')
    if(-not(Test-Path -LiteralPath $path -PathType Leaf)){$inventoryValid=$false;continue}
    if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256){$inventoryValid=$false}
  }
}catch{$inventoryValid=$false}
$parseErrors=0
$psScripts=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File
foreach($file in $psScripts){
  $tokens=$null;$errors=$null
  [void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
  if($errors.Count -gt 0){$parseErrors += $errors.Count}
}
$rawUnsafe=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File | Select-String -Pattern '\\$[A-Za-z_][A-Za-z0-9_]*:'
$unsafe=@($rawUnsafe | Where-Object { $_.Matches.Value -notmatch '^\\$(env|global|script|local|private|using):' })
$contract=$null
$contractValid=$true
try{
  $contract=Get-Content -LiteralPath (Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  if($contract.repair_scope -ne 'IDEMPOTENT_PREFLIGHT_AND_EXACT_POSTIMAGE_RECONCILIATION_ONLY'){$contractValid=$false}
  if($contract.manifest_binding_schema_version -ne '2'){$contractValid=$false}
}catch{$contractValid=$false}
$postimageValid=$true
try{
  $post=Get-Content -LiteralPath (Join-Path $PackageRoot 'contracts\expected_postimage_hashes_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach($entry in $post.files){
    $path=Join-Path $PackageRoot ([string]$entry.path).Replace('/','\')
    if(-not(Test-Path -LiteralPath $path -PathType Leaf)){$postimageValid=$false;continue}
    if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256){$postimageValid=$false}
  }
}catch{$postimageValid=$false}
$allOk=($missing.Count -eq 0 -and $inventoryValid -and $parseErrors -eq 0 -and $unsafe.Count -eq 0 -and $contractValid -and $postimageValid)
("CANDIDATE_PACKAGE_INVENTORY={0}" -f $(if($missing.Count -eq 0){'PASS'}else{'FAIL'}))
("CANDIDATE_INVENTORY_HASHES={0}" -f $(if($inventoryValid){'PASS'}else{'FAIL'}))
("CANDIDATE_POWERSHELL_PARSE={0}" -f $(if($parseErrors -eq 0){'PASS'}else{'FAIL'}))
("CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN={0}" -f $(if($unsafe.Count -eq 0){'PASS'}else{'FAIL'}))
("CANDIDATE_POSTIMAGE_HASH_CONTRACT={0}" -f $(if($postimageValid){'PASS'}else{'FAIL'}))
("CANDIDATE_IDEMPOTENCY_CONTRACT={0}" -f $(if($contractValid){'PASS'}else{'FAIL'}))
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'PROJECT_MUTATION=NONE'
'SERVICE_START=NONE'
'EXTERNAL_NETWORK=NONE'
("CANDIDATE_SYNTAX_RESULT={0}" -f $(if($allOk){'PASS'}else{'FAIL'}))
if(-not $allOk){throw 'IDEMPOTENCY_POSTIMAGE_RECONCILIATION_REPAIR_CANDIDATE_SYNTAX_FAILED'}
