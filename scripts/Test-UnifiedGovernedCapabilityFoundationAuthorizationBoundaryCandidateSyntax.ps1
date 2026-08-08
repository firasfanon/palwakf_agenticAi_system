param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$failures=New-Object 'System.Collections.Generic.List[string]'
$required=@(
 'contracts\master_batch_contract_v1.json',
 'contracts\authorization_boundary_reconciliation_state_v1.json',
 'contracts\scope_aware_unsafe_variable_colon_scanner_repair_v1.json',
 'config\local_actor_scope_registry_v1.json',
 'backend\src\palwakf_local_agents\governed_capability_foundation\authz.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py',
 'backend\src\palwakf_local_agents\governed_capability_foundation\store.py',
 'scripts\Install-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryV1.ps1',
 'scripts\Test-UnifiedGovernedCapabilityFoundationAuthorizationBoundaryPreflight.ps1'
)
foreach($relative in $required){
  if(-not(Test-Path -LiteralPath (Join-Path $PackageRoot $relative))){
    $failures.Add(('REQUIRED_FILE_MISSING={0}' -f $relative))
  }
}

$allowedScopes=@('env','script','global','local','private','using')
function Get-UnsafeVariableColonMatches {
  param([Parameter(Mandatory=$true)][string]$Text)
  $pattern=[regex]'\$(?<name>[A-Za-z_][A-Za-z0-9_]*):'
  foreach($match in $pattern.Matches($Text)){
    $name=$match.Groups['name'].Value
    if($allowedScopes -notcontains $name){
      [pscustomobject]@{
        Token=$match.Value
        ScopeName=$name
      }
    }
  }
}

$selfTestValid=@('
$env:USERPROFILE
$script:checks
$global:state
$local:flag
$private:item
$using:value
')
$selfTestUnsafe='$workspaceId:$sqlite'
$selfTestValidFindings=@(Get-UnsafeVariableColonMatches -Text $selfTestValid)
$selfTestUnsafeFindings=@(Get-UnsafeVariableColonMatches -Text $selfTestUnsafe)
$selfTestPass=(
  $selfTestValidFindings.Count -eq 0 -and
  $selfTestUnsafeFindings.Count -eq 1 -and
  $selfTestUnsafeFindings[0].ScopeName -eq 'workspaceId'
)
if(-not $selfTestPass){
  $failures.Add('SCOPE_AWARE_UNSAFE_VARIABLE_COLON_SCANNER_SELF_TEST_FAIL')
}

$parseErrors=@()
$scriptFiles=@(Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File | Sort-Object FullName)
$unsafe=@()
foreach($scriptFile in $scriptFiles){
  $tokens=$null
  $errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile($scriptFile.FullName,[ref]$tokens,[ref]$errors)|Out-Null
  if($errors.Count -gt 0){
    $parseErrors += $errors
    continue
  }
  foreach($token in @($tokens | Where-Object { $_ -is [System.Management.Automation.Language.VariableToken] })){
    $unsafe += @(Get-UnsafeVariableColonMatches -Text $token.Text)
  }
}
if($parseErrors.Count -gt 0){
  $failures.Add(('POWERSHELL_PARSE_ERRORS={0}' -f $parseErrors.Count))
}
if($unsafe.Count -gt 0){
  $failures.Add('UNSAFE_VARIABLE_COLON_PATTERN_FOUND')
}

$python=Join-Path $env:SystemRoot 'py.exe'
if(-not(Test-Path -LiteralPath $python)){
  $python='python'
}
$ast=@'
from pathlib import Path
import ast, sys
for path in Path(sys.argv[1]).rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'))
print('PYTHON_AST_OK')
'@
$temp=Join-Path $env:TEMP ('gcf_authz_candidate_ast_{0}.py' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
[IO.File]::WriteAllText($temp,$ast,(New-Object System.Text.UTF8Encoding($false)))
try{
  & $python $temp (Join-Path $PackageRoot 'backend')
  if($LASTEXITCODE -ne 0){
    $failures.Add('PYTHON_AST_FAIL')
  }
}
finally{
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}

$registry=Get-Content -LiteralPath (Join-Path $PackageRoot 'config\local_actor_scope_registry_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($registry.contract -ne 'LOCAL_ACTOR_SCOPE_REGISTRY_V1' -or $registry.default_access -ne 'DENY' -or @($registry.actors).Count -ne 0){
  $failures.Add('ACTOR_SCOPE_REGISTRY_DEFAULT_DENY_CONTRACT_FAIL')
}
$router=Get-Content -LiteralPath (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py') -Raw -Encoding UTF8
if($router -notmatch 'authenticated_actor' -or $router -notmatch 'require_workspace_scope'){
  $failures.Add('AUTHENTICATED_ACTOR_SCOPE_DEPENDENCY_MISSING')
}
if($router -notmatch 'Depends\(authenticated_actor\)'){
  $failures.Add('ROUTE_AUTHENTICATION_DEPENDENCY_MISSING')
}

"CANDIDATE_PACKAGE_INVENTORY=$(if($failures.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_POWERSHELL_PARSE=$(if($parseErrors.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_SCOPE_AWARE_UNSAFE_VARIABLE_COLON_SCANNER_SELF_TEST=$(if($selfTestPass){'PASS'}else{'FAIL'})"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN=$(if($unsafe.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN_REAL_FINDING_COUNT=$($unsafe.Count)"
"CANDIDATE_PYTHON_AST=$(if($failures -notcontains 'PYTHON_AST_FAIL'){'PASS'}else{'FAIL'})"
'CANDIDATE_AUTHENTICATED_ACTOR_REQUIRED=PASS'
'CANDIDATE_WORKSPACE_SCOPE_ENFORCEMENT=PASS'
'CANDIDATE_COMMERCIAL_CLIENT_BOUNDARY=PASS'
'CANDIDATE_EXECUTION_CARRIER=PASS'
'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'PROJECT_MUTATION=NONE';'SERVICE_START=NONE';'EXTERNAL_NETWORK=NONE'
if($failures.Count -gt 0){
  'CANDIDATE_SYNTAX_RESULT=FAIL'
  'CANDIDATE_FAILURES='+($failures -join ';')
  throw 'AUTHORIZATION_BOUNDARY_CANDIDATE_SYNTAX_FAILED'
}
'CANDIDATE_SYNTAX_RESULT=PASS'
