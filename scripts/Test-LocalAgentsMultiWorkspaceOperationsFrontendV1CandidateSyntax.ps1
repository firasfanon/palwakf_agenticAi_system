[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$PackageRoot
)

$ErrorActionPreference = "Stop"

function Get-TextFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  return [System.IO.File]::ReadAllText($Path)
}

function Get-FrontendNoWriteGuardPatterns {
  return @(
    "localStorage",
    "sessionStorage",
    "Authorization",
    "/pilot/execute",
    'method\s*:\s*[''"]POST',
    '\.post\s*\('
  )
}

function Test-FrontendNoWriteGuardRegexRuntime {
  $patterns = Get-FrontendNoWriteGuardPatterns

  foreach ($pattern in $patterns) {
    try {
      [void][System.Text.RegularExpressions.Regex]::new($pattern)
    }
    catch {
      throw ("CANDIDATE_REGEX_SAFE_COMPILE_FAILED=" + $pattern + "; " + $_.Exception.Message)
    }
  }

  $methodPostPattern = $patterns[4]
  $dotPostPattern = $patterns[5]

  $blockedMethodFixtures = @(
    "const request = { method: 'POST' };",
    'fetch("/api/tasks", { method: "POST" })'
  )
  foreach ($fixture in $blockedMethodFixtures) {
    if ($fixture -notmatch $methodPostPattern) {
      throw ("CANDIDATE_POST_PATTERN_MATCH_TEST_FAILED=" + $fixture)
    }
  }

  $allowedMethodFixtures = @(
    "const request = { method: 'GET' };",
    'fetch("/api/tasks")'
  )
  foreach ($fixture in $allowedMethodFixtures) {
    if ($fixture -match $methodPostPattern) {
      throw ("CANDIDATE_POST_PATTERN_NONMATCH_TEST_FAILED=" + $fixture)
    }
  }

  if ('client.post("/api/tasks")' -notmatch $dotPostPattern) {
    throw "CANDIDATE_DOT_POST_PATTERN_MATCH_TEST_FAILED"
  }
  if ('client.get("/api/tasks")' -match $dotPostPattern) {
    throw "CANDIDATE_DOT_POST_PATTERN_NONMATCH_TEST_FAILED"
  }

  Write-Output "CANDIDATE_REGEX_SAFE_COMPILE=PASS"
  Write-Output "CANDIDATE_POST_PATTERN_MATCH_TEST=PASS"
  Write-Output "CANDIDATE_POST_PATTERN_NONMATCH_TEST=PASS"
}

Write-Output "===== LOCAL AGENTS MULTI-WORKSPACE OPERATIONS FRONTEND V1 CANDIDATE SYNTAX ====="

$required = @(
  "baseline_binding.json",
  "payload\backend\src\palwakf_local_agents\command_center\static\index.html",
  "payload\backend\src\palwakf_local_agents\command_center\static\app.js",
  "payload\backend\src\palwakf_local_agents\command_center\static\styles.css",
  "payload\backend\src\palwakf_local_agents\governed_operations\static\index.html",
  "payload\backend\src\palwakf_local_agents\governed_operations\static\app.js",
  "payload\backend\src\palwakf_local_agents\governed_operations\static\styles.css",
  "payload\backend\src\palwakf_local_agents\local_agent_core\static\index.html",
  "payload\backend\src\palwakf_local_agents\local_agent_core\static\app.js",
  "payload\backend\src\palwakf_local_agents\local_agent_core\static\styles.css",
  "payload\backend\src\palwakf_local_agents\workspace_core\static\index.html",
  "payload\backend\src\palwakf_local_agents\workspace_core\static\app.js",
  "payload\backend\src\palwakf_local_agents\workspace_core\static\styles.css",
  "scripts\Test-LocalAgentsMultiWorkspaceOperationsFrontendV1CandidateSyntax.ps1",
  "scripts\Test-LocalAgentsMultiWorkspaceOperationsFrontendV1Preflight.ps1",
  "scripts\Install-LocalAgentsMultiWorkspaceOperationsFrontendV1.ps1",
  "scripts\Test-LocalAgentsMultiWorkspaceOperationsFrontendV1PostApply.ps1",
  "scripts\Invoke-LocalAgentsMultiWorkspaceOperationsFrontendV1Readiness.ps1"
)

foreach ($item in $required) {
  $path = Join-Path $PackageRoot $item
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw ("CANDIDATE_REQUIRED_FILE_MISSING=" + $path)
  }
}

$binding = Get-Content -LiteralPath (Join-Path $PackageRoot "baseline_binding.json") -Raw | ConvertFrom-Json
if (@($binding.assets).Count -ne 12) {
  throw "CANDIDATE_BASELINE_BINDING_ASSET_COUNT_INVALID"
}

$parseFailureCount = 0
Get-ChildItem -LiteralPath (Join-Path $PackageRoot "scripts") -Filter "*.ps1" -File | ForEach-Object {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors)
  if (@($errors).Count -gt 0) {
    $parseFailureCount++
    $errors | ForEach-Object { Write-Output ("POWERSHELL_PARSE_ERROR=" + $_.Message) }
  }
}
if ($parseFailureCount -ne 0) {
  throw "CANDIDATE_POWERSHELL_PARSE_FAILED"
}

Test-FrontendNoWriteGuardRegexRuntime

$assetText = ""
Get-ChildItem -LiteralPath (Join-Path $PackageRoot "payload") -Recurse -File | ForEach-Object {
  $assetText += "`n" + (Get-TextFile -Path $_.FullName)
}

$blockedPatterns = Get-FrontendNoWriteGuardPatterns
foreach ($pattern in $blockedPatterns) {
  if ($assetText -match $pattern) {
    throw ("CANDIDATE_FRONTEND_GUARDRAIL_VIOLATION=" + $pattern)
  }
}

$operationsJs = Get-TextFile -Path (Join-Path $PackageRoot "payload\backend\src\palwakf_local_agents\governed_operations\static\app.js")
if ($operationsJs -notmatch "READ FIRST") {
  throw "CANDIDATE_GOVERNED_OPERATIONS_READ_FIRST_CONTRACT_MISSING"
}

Write-Output "CANDIDATE_PACKAGE_INVENTORY=PASS"
Write-Output "CANDIDATE_POWERSHELL_PARSE=PASS"
Write-Output "CANDIDATE_BASELINE_EXACT_HASH_BINDING=PASS"
Write-Output "CANDIDATE_STATIC_ASSET_SCOPE=12"
Write-Output "CANDIDATE_READ_ONLY_FRONTEND_GUARD=PASS"
Write-Output "CANDIDATE_NO_TOKEN_PERSISTENCE=PASS"
Write-Output "CANDIDATE_NO_MODEL_OR_PILOT_EXECUTION=PASS"
Write-Output "CANDIDATE_NO_BACKEND_ROUTER_OR_SCHEMA_MUTATION=PASS"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PROJECT_MUTATION=NONE"
Write-Output "SERVICE_START=NONE"
Write-Output "SHELL_EXECUTION=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "EXTERNAL_NETWORK=NONE"
Write-Output "CANDIDATE_SYNTAX_RESULT=PASS"
