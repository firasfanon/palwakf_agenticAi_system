param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = 'Stop'

$required = @(
  'README_AR.md',
  'MANIFEST_FRONTEND_V1_BASELINE_EMPTY_COLLECTION_BINDING_REPAIR.md',
  'RUN_GUIDE_EMPTY_COLLECTION_BINDING_REPAIR_AR.md',
  'docs/FRONTEND_ARCHITECTURE_AR.md',
  'scripts/Test-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineCarrierSyntax.ps1',
  'scripts/Test-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineCarrierRuntime.ps1',
  'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaseline.ps1',
  'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineWhatIf.ps1',
  'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaselineRunner.ps1'
)

$failures = New-Object System.Collections.ArrayList
foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    [void]$failures.Add(('MISSING_REQUIRED_FILE={0}' -f $relative))
  }
}

$scriptDirectory = Join-Path $PackageRoot 'scripts'
if (-not (Test-Path -LiteralPath $scriptDirectory -PathType Container)) {
  [void]$failures.Add('SCRIPTS_DIRECTORY_MISSING')
}

$parseErrors = New-Object System.Collections.ArrayList
$scriptFiles = @()
if (Test-Path -LiteralPath $scriptDirectory -PathType Container) {
  $scriptFiles = @(Get-ChildItem -LiteralPath $scriptDirectory -Filter '*.ps1' -File -Recurse | Sort-Object FullName)
}
foreach ($scriptFile in $scriptFiles) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile(
    $scriptFile.FullName,
    [ref]$tokens,
    [ref]$errors
  )
  if (($null -ne $errors) -and ($errors.Count -gt 0)) {
    foreach ($errorRecord in $errors) {
      [void]$parseErrors.Add(('{0}:{1}' -f $scriptFile.Name, $errorRecord.Message))
    }
  }
}

$genericListHit = $false
foreach ($scriptFile in $scriptFiles) {
  $scriptText = Get-Content -LiteralPath $scriptFile.FullName -Raw -Encoding UTF8
  if ($scriptText -match 'System\.Collections\.Generic\.List') {
    $genericListHit = $true
    [void]$failures.Add(('GENERIC_LIST_RUNTIME_RISK_FOUND={0}' -f $scriptFile.Name))
  }
}

$baselineScriptPath = Join-Path $PackageRoot 'scripts/Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1FinalBaseline.ps1'
$emptyCollectionBindingGuard = $false
if (Test-Path -LiteralPath $baselineScriptPath -PathType Leaf) {
  $baselineScriptText = Get-Content -LiteralPath $baselineScriptPath -Raw -Encoding UTF8
  $emptyCollectionBindingGuard = (
    ($baselineScriptText -match '\[AllowNull\(\)\]\[object\]\$Target') -and
    ($baselineScriptText -match 'INVENTORY_TARGET_NULL') -and
    ($baselineScriptText -match 'INVENTORY_TARGET_NOT_I_LIST') -and
    ($baselineScriptText -notmatch '\[Parameter\(Mandatory\s*=\s*\$true\)\]\[System\.Collections\.ArrayList\]\$Target')
  )
  if (-not $emptyCollectionBindingGuard) {
    [void]$failures.Add('EMPTY_COLLECTION_BINDING_GUARD_MISSING')
  }
}
else {
  [void]$failures.Add('BASELINE_SCRIPT_MISSING_FOR_EMPTY_COLLECTION_GUARD')
}

$manifestPath = Join-Path $PackageRoot 'MANIFEST_FRONTEND_V1_BASELINE_EMPTY_COLLECTION_BINDING_REPAIR.md'
$contractPass = $false
if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
  $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
  $contractPass = (
    ($manifest -match 'No fake successful data') -and
    ($manifest -match 'No hard-coded actor token') -and
    ($manifest -match 'No token persistence') -and
    ($manifest -match 'No cross-workspace selector leakage') -and
    ($manifest -match 'No cross-client commercial data exposure')
  )
  if (-not $contractPass) {
    [void]$failures.Add('MANIFEST_GOVERNANCE_CONTRACT_MISSING')
  }
}

'===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 FINAL BASELINE CARRIER SYNTAX ====='
('CANDIDATE_PACKAGE_INVENTORY={0}' -f $(if ($failures.Count -eq 0) { 'PASS' } else { 'FAIL' }))
('CANDIDATE_POWERSHELL_PARSE={0}' -f $(if ($parseErrors.Count -eq 0) { 'PASS' } else { 'FAIL' }))
('CANDIDATE_NO_GENERIC_LIST_RUNTIME_BINDING={0}' -f $(if (-not $genericListHit) { 'PASS' } else { 'FAIL' }))
('CANDIDATE_EMPTY_COLLECTION_BINDING_GUARD={0}' -f $(if ($emptyCollectionBindingGuard) { 'PASS' } else { 'FAIL' }))
('CANDIDATE_FRONTEND_GOVERNANCE_CONTRACT={0}' -f $(if ($contractPass) { 'PASS' } else { 'FAIL' }))
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'PROJECT_MUTATION=NONE'
'SERVICE_START=NONE'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'EXTERNAL_NETWORK=NONE'

if ($parseErrors.Count -gt 0) {
  ('CANDIDATE_PARSE_ERRORS={0}' -f ($parseErrors -join ';'))
}
if ($failures.Count -gt 0) {
  ('CANDIDATE_FAILURES={0}' -f ($failures -join ';'))
}

if (($parseErrors.Count -gt 0) -or ($failures.Count -gt 0)) {
  'CANDIDATE_SYNTAX_RESULT=FAIL'
  throw 'LOCAL_AGENTS_MULTI_WORKSPACE_OPERATIONS_FRONTEND_V1_FINAL_BASELINE_CARRIER_SYNTAX_FAILED'
}

'CANDIDATE_SYNTAX_RESULT=PASS'
