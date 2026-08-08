#requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $PackageRoot -PathType Container)) {
  throw "PACKAGE_ROOT_NOT_FOUND=$PackageRoot"
}

$required = @(
  "README_AR.md",
  "MANIFEST_COMPREHENSIVE_LOCAL_AGENTS_PROJECT_STATE_AND_DEBT_REVIEW_V1.md",
  "RUN_GUIDE_COMPREHENSIVE_PROJECT_REVIEW_AR.md",
  "candidate\accepted_baseline_and_scope_v1.json",
  "candidate\review_scope_v1.json",
  "candidate\known_open_debts_v1.json",
  "candidate\repair_scope_v1.json",
  "docs\REVIEW_CRITERIA_AR.md",
  "scripts\Invoke-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1.ps1",
  "scripts\Test-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1PackageSyntax.ps1",
  "PACKAGE_INVENTORY.json"
)

$inventoryFailures = New-Object 'System.Collections.Generic.List[string]'
$parseFailures = New-Object 'System.Collections.Generic.List[string]'
$encodingFailures = New-Object 'System.Collections.Generic.List[string]'
$contractFailures = New-Object 'System.Collections.Generic.List[string]'

foreach ($relative in $required) {
  $path = Join-Path $PackageRoot $relative
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    $inventoryFailures.Add("REQUIRED_FILE_MISSING=$relative")
  }
}

$inventoryPath = Join-Path $PackageRoot "PACKAGE_INVENTORY.json"
if (Test-Path -LiteralPath $inventoryPath -PathType Leaf) {
  try {
    $inventory = Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($item in $inventory.files) {
      $path = Join-Path $PackageRoot ([string]$item.path)
      if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $inventoryFailures.Add("INVENTORY_FILE_MISSING=$($item.path)")
      }
      else {
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne ([string]$item.sha256).ToLowerInvariant()) {
          $inventoryFailures.Add("INVENTORY_HASH_MISMATCH=$($item.path)")
        }
      }
    }
  }
  catch {
    $inventoryFailures.Add("PACKAGE_INVENTORY_INVALID=$($_.Exception.Message)")
  }
}

$scriptRelatives = @(
  "scripts\Invoke-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1.ps1",
  "scripts\Test-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1PackageSyntax.ps1"
)
foreach ($relative in $scriptRelatives) {
  $path = Join-Path $PackageRoot $relative
  if (Test-Path -LiteralPath $path -PathType Leaf) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors)
    if ($errors.Count -ne 0) {
      $parseFailures.Add("POWERSHELL_PARSE_ERRORS=$($relative):$($errors.Count)")
    }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191)
    if (-not $hasBom) {
      $encodingFailures.Add("UTF8_BOM_MISSING=$relative")
    }
  }
}

$reviewPath = Join-Path $PackageRoot "scripts\Invoke-ComprehensiveLocalAgentsProjectStateAndDebtReviewV1.ps1"
if (Test-Path -LiteralPath $reviewPath -PathType Leaf) {
  $reviewBytes = [System.IO.File]::ReadAllBytes($reviewPath)
  $reviewHasBom = ($reviewBytes.Length -ge 3 -and $reviewBytes[0] -eq 239 -and $reviewBytes[1] -eq 187 -and $reviewBytes[2] -eq 191)
  $hasNonAscii = $false
  $reviewStartIndex = 0
  if ($reviewHasBom) { $reviewStartIndex = 3 }
  for ($index = $reviewStartIndex; $index -lt $reviewBytes.Length; $index++) {
    if ($reviewBytes[$index] -gt 127) { $hasNonAscii = $true; break }
  }
  if ($hasNonAscii) {
    $encodingFailures.Add("RUNTIME_SCRIPT_NOT_ASCII_ONLY")
  }
  $reviewText = [System.Text.Encoding]::UTF8.GetString($reviewBytes)
  if ($reviewText -notmatch '\$ASCII_ONLY_RUNTIME_STRINGS\s*=\s*\$true') {
    $contractFailures.Add("ASCII_RUNTIME_MARKER_MISSING")
  }
  if ($reviewText -notmatch '\$READ_ONLY_AUDIT\s*=\s*\$true') {
    $contractFailures.Add("READ_ONLY_RUNTIME_MARKER_MISSING")
  }
  if ($reviewText -notmatch '\$REPORT_CONSTRUCTION_RUNTIME_SELF_TEST\s*=\s*\$true') {
    $contractFailures.Add("REPORT_RUNTIME_SELF_TEST_MARKER_MISSING")
  }
  try {
    $runtimeSelfTestOutput = @(& $reviewPath -RuntimeSelfTestOnly 2>&1)
    $runtimeSelfTestExit = $LASTEXITCODE
    if ($runtimeSelfTestExit -ne 0 -or (($runtimeSelfTestOutput -join "`n") -notmatch "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST=PASS")) {
      $contractFailures.Add("REPORT_RUNTIME_SELF_TEST_FAILED")
    }
  }
  catch {
    $contractFailures.Add("REPORT_RUNTIME_SELF_TEST_EXCEPTION=$($_.Exception.Message)")
  }
}

try {
  $baselinePath = Join-Path $PackageRoot "candidate\accepted_baseline_and_scope_v1.json"
  $scopePath = Join-Path $PackageRoot "candidate\review_scope_v1.json"
  $repairPath = Join-Path $PackageRoot "candidate\repair_scope_v1.json"
  $baseline = Get-Content -LiteralPath $baselinePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $scope = Get-Content -LiteralPath $scopePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $repair = Get-Content -LiteralPath $repairPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($baseline.contract -ne "ACCEPTED_LOCAL_AGENTS_BASELINE_20260630") { $contractFailures.Add("BASELINE_CONTRACT_INVALID") }
  if ($scope.contract -ne "COMPREHENSIVE_LOCAL_AGENTS_PROJECT_STATE_AND_DEBT_REVIEW_V1_READ_ONLY") { $contractFailures.Add("REVIEW_SCOPE_CONTRACT_INVALID") }
  if ($scope.target_mutation -ne "NONE") { $contractFailures.Add("REVIEW_SCOPE_NOT_READ_ONLY") }
  if ($repair.repair_scope -ne "REPORT_CONSTRUCTION_AND_SERIALIZATION_ONLY") { $contractFailures.Add("REPAIR_SCOPE_INVALID") }
  if ($repair.project_mutation -ne "NONE") { $contractFailures.Add("REPAIR_PROJECT_MUTATION_NOT_NONE") }
}
catch {
  $contractFailures.Add("CANDIDATE_JSON_INVALID=$($_.Exception.Message)")
}

$allFailures = @($inventoryFailures) + @($parseFailures) + @($encodingFailures) + @($contractFailures)
"CANDIDATE_PACKAGE_INVENTORY=$(if ($inventoryFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_INVENTORY_HASHES=$(if ($inventoryFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_POWERSHELL_PARSE=$(if ($parseFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_UTF8_BOM_CONTRACT=$(if ($encodingFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
$asciiContractPass = ($encodingFailures.Count -eq 0 -and -not ($contractFailures -contains "ASCII_RUNTIME_MARKER_MISSING"))
"CANDIDATE_ASCII_RUNTIME_CONTRACT=$(if ($asciiContractPass) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_BASELINE_AND_SCOPE_JSON=$(if ($contractFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
"CANDIDATE_REPAIR_SCOPE=$(if ($contractFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
$runtimeSelfTestFailures = @($contractFailures | Where-Object { $_ -like "REPORT_RUNTIME_SELF_TEST*" })
"CANDIDATE_REPORT_CONSTRUCTION_RUNTIME_SELF_TEST=$(if ($runtimeSelfTestFailures.Count -eq 0) { 'PASS' } else { 'FAIL' })"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PROJECT_MUTATION=NONE"
"SERVICE_START=NONE"
"EXTERNAL_NETWORK=NONE"

if ($allFailures.Count -gt 0) {
  "CANDIDATE_SYNTAX_RESULT=FAIL"
  "CANDIDATE_FAILURES=$($allFailures -join ';')"
  throw "COMPREHENSIVE_REVIEW_REPAIR_PACKAGE_SYNTAX_FAILED"
}

"CANDIDATE_SYNTAX_RESULT=PASS"
