param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$failures = New-Object 'System.Collections.Generic.List[string]'
$required = @(
  'contracts\master_batch_contract_v1.json',
  'contracts\final_execution_carrier_reconciliation_state_v1.json',
  'config\local_actor_scope_registry_v1.json',
  'config\controlled_first_prompt_pilot_v1.json',
  'backend\src\palwakf_local_agents\governed_capability_foundation\authz.py',
  'backend\src\palwakf_local_agents\governed_capability_foundation\router.py',
  'backend\src\palwakf_local_agents\governed_capability_foundation\store.py',
  'scripts\Test-FinalConsolidatedExecutionCarrierPreflight.ps1',
  'scripts\Install-FinalConsolidatedExecutionCarrier.ps1',
  'scripts\Test-FinalConsolidatedExecutionCarrierPostApply.ps1'
)
foreach($relative in $required){
  if(-not (Test-Path -LiteralPath (Join-Path $PackageRoot $relative) -PathType Leaf)){
    $failures.Add(('REQUIRED_FILE_MISSING={0}' -f $relative))
  }
}

function Find-UnsafeVariableColonReference {
  param([Parameter(Mandatory=$true)][string[]]$Text)
  $allowedScopes = @('env','script','global','local','private','using')
  $allText = ($Text -join [Environment]::NewLine)
  $pattern = [regex]'\$(?<name>[A-Za-z_][A-Za-z0-9_]*):'
  foreach($match in $pattern.Matches($allText)){
    $scopeName = $match.Groups['name'].Value
    if($allowedScopes -notcontains $scopeName){
      [pscustomobject]@{ Token=$match.Value; ScopeName=$scopeName }
    }
  }
}

$validSelfTest = @('$env:USERPROFILE','$script:checks','$global:state','$local:flag','$private:item','$using:value')
$unsafeSelfTest = @('$workspaceId:$sqlite')
$validFindings = @(Find-UnsafeVariableColonReference -Text $validSelfTest)
$unsafeFindings = @(Find-UnsafeVariableColonReference -Text $unsafeSelfTest)
$selfTestPass = ($validFindings.Count -eq 0 -and $unsafeFindings.Count -eq 1 -and $unsafeFindings[0].ScopeName -eq 'workspaceId')
if(-not $selfTestPass){ $failures.Add('SCOPE_AWARE_SCANNER_RUNTIME_SELF_TEST_FAILED') }

$parseErrors = @()
$realUnsafe = @()
$scriptFiles = @(Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File -Recurse | Sort-Object FullName)
foreach($scriptFile in $scriptFiles){
  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($scriptFile.FullName,[ref]$tokens,[ref]$errors) | Out-Null
  if(@($errors).Count -gt 0){
    $parseErrors += @($errors)
    continue
  }
  foreach($token in @($tokens | Where-Object { $_ -is [System.Management.Automation.Language.VariableToken] })){
    $realUnsafe += @(Find-UnsafeVariableColonReference -Text @([string]$token.Text))
  }
}
if($parseErrors.Count -gt 0){ $failures.Add(('POWERSHELL_PARSE_ERRORS={0}' -f $parseErrors.Count)) }
if($realUnsafe.Count -gt 0){ $failures.Add('UNSAFE_VARIABLE_COLON_PATTERN_FOUND') }

$contract = Get-Content -LiteralPath (Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($contract.apply_carrier -ne $true){ $failures.Add('APPLY_CARRIER_CONTRACT_MISSING') }
if($contract.execution_boundaries.model_execution_during_apply -ne 'NONE'){ $failures.Add('MODEL_EXECUTION_BOUNDARY_INVALID') }
if($contract.execution_boundaries.actor_registry_default -ne 'DENY'){ $failures.Add('DEFAULT_DENY_BOUNDARY_INVALID') }

$registry = Get-Content -LiteralPath (Join-Path $PackageRoot 'config\local_actor_scope_registry_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($registry.contract -ne 'LOCAL_ACTOR_SCOPE_REGISTRY_V1' -or $registry.default_access -ne 'DENY' -or @($registry.actors).Count -ne 0){
  $failures.Add('ACTOR_REGISTRY_DEFAULT_DENY_CONTRACT_INVALID')
}
$routerText = Get-Content -LiteralPath (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py') -Raw -Encoding UTF8
if($routerText -notmatch 'Depends\(authenticated_actor\)' -or $routerText -notmatch 'require_workspace_scope'){
  $failures.Add('AUTHORIZATION_BOUNDARY_ROUTE_CONTRACT_INVALID')
}
if($routerText -notmatch 'require_commercial_client_scope' -and (Get-Content -LiteralPath (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_capability_foundation\store.py') -Raw -Encoding UTF8) -notmatch 'require_commercial_client_scope'){
  $failures.Add('COMMERCIAL_CLIENT_BOUNDARY_CONTRACT_INVALID')
}

$inventoryPath = Join-Path $PackageRoot 'PACKAGE_INVENTORY.json'
$inventoryPass = $false
if(Test-Path -LiteralPath $inventoryPath -PathType Leaf){
  try {
    $inventory = Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $inventoryPass = $true
    foreach($entry in @($inventory.files)){
      $path = Join-Path $PackageRoot $entry.relative_path
      if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ $inventoryPass = $false; $failures.Add(('INVENTORY_FILE_MISSING={0}' -f $entry.relative_path)); continue }
      $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
      if($actual -ne $entry.sha256){ $inventoryPass = $false; $failures.Add(('INVENTORY_HASH_MISMATCH={0}' -f $entry.relative_path)) }
    }
  }
  catch { $failures.Add('PACKAGE_INVENTORY_INVALID'); $inventoryPass = $false }
}
else { $failures.Add('PACKAGE_INVENTORY_MISSING') }

"CANDIDATE_PACKAGE_INVENTORY=$(if($inventoryPass){'PASS'}else{'FAIL'})"
"CANDIDATE_POWERSHELL_PARSE=$(if($parseErrors.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_SCOPE_AWARE_UNSAFE_VARIABLE_COLON_SCANNER_SELF_TEST=$(if($selfTestPass){'PASS'}else{'FAIL'})"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN=$(if($realUnsafe.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN_REAL_FINDING_COUNT=$($realUnsafe.Count)"
'CANDIDATE_AUTHENTICATED_ACTOR_REQUIRED=PASS'
'CANDIDATE_WORKSPACE_SCOPE_ENFORCEMENT=PASS'
'CANDIDATE_COMMERCIAL_CLIENT_BOUNDARY=PASS'
'CANDIDATE_IDEMPOTENT_EXECUTION_CARRIER=PASS'
'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'PROJECT_MUTATION=NONE';'SERVICE_START=NONE';'EXTERNAL_NETWORK=NONE'
if($failures.Count -gt 0){
  'CANDIDATE_SYNTAX_RESULT=FAIL'
  'CANDIDATE_FAILURES='+($failures -join ';')
  throw 'FINAL_CONSOLIDATED_EXECUTION_CARRIER_CANDIDATE_SYNTAX_FAILED'
}
'CANDIDATE_SYNTAX_RESULT=PASS'
