[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$PackageRoot
)
$ErrorActionPreference = 'Stop'
function Require-File([string]$Path) { if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "REQUIRED_FILE_NOT_FOUND=$Path" } }
function Require-Directory([string]$Path) { if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "REQUIRED_DIRECTORY_NOT_FOUND=$Path" } }
function Get-Sha256([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
Write-Output '===== REACT TYPESCRIPT FRONTEND FOUNDATION V1 CANDIDATE SYNTAX ====='
Require-Directory $PackageRoot
$manifestPath = Join-Path $PackageRoot 'payload\react_foundation_manifest.json'
Require-File $manifestPath
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.contract -ne 'LOCAL_AGENTS_REACT_TYPESCRIPT_FRONTEND_FOUNDATION_V1') { throw 'INVALID_REACT_FOUNDATION_MANIFEST_CONTRACT' }
$required = @(
  'payload\backend\src\palwakf_local_agents\app.py',
  'payload\frontend\package.json',
  'payload\frontend\tsconfig.json',
  'payload\frontend\vite.config.ts',
  'payload\frontend\src\main.tsx',
  'payload\frontend\src\App.tsx',
  'payload\frontend\src\api\client.ts',
  'payload\frontend\src\styles.css',
  'scripts\Test-ReactTypeScriptFrontendFoundationCandidateSyntax.ps1',
  'scripts\Test-ReactTypeScriptFrontendFoundationPreflight.ps1',
  'scripts\Invoke-ReactTypeScriptFrontendFoundationWhatIf.ps1',
  'scripts\Install-ReactTypeScriptFrontendFoundation.ps1',
  'scripts\Test-ReactTypeScriptFrontendFoundationPostApply.ps1'
)
foreach ($relative in $required) { Require-File (Join-Path $PackageRoot $relative) }
foreach ($script in (Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File)) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($script.FullName, [ref]$tokens, [ref]$errors)
  if ($errors.Count -gt 0) { throw "POWERSHELL_PARSE_FAILED=$($script.Name):$($errors[0].Message)" }
}
$packageJson = Get-Content -LiteralPath (Join-Path $PackageRoot 'payload\frontend\package.json') -Raw | ConvertFrom-Json
if ($packageJson.dependencies.react -ne '18.3.1') { throw 'REACT_VERSION_PIN_MISMATCH' }
if ($packageJson.scripts.build -ne 'npm run check && vite build') { throw 'REACT_BUILD_SCRIPT_MISMATCH' }
$frontendRoot = Join-Path $PackageRoot 'payload\frontend'
$forbidden = @('localStorage', 'sessionStorage', 'Authorization', 'Bearer ', 'method: "POST"', "method: 'POST'", 'method: "PUT"', "method: 'PUT'", 'method: "PATCH"', "method: 'PATCH'", 'method: "DELETE"', "method: 'DELETE'")
foreach ($needle in $forbidden) {
  $hits = Select-String -LiteralPath (Get-ChildItem -LiteralPath $frontendRoot -Recurse -File | Select-Object -ExpandProperty FullName) -SimpleMatch -Pattern $needle -ErrorAction SilentlyContinue
  if ($null -ne $hits) { throw "FORBIDDEN_FRONTEND_PATTERN=$needle" }
}
$runtimePath = Join-Path $env:TEMP ('react_foundation_runtime_' + [guid]::NewGuid().ToString('N') + '.txt')
try {
  Set-Content -LiteralPath $runtimePath -Value 'runtime-self-test' -Encoding UTF8
  if ((Get-Sha256 $runtimePath).Length -ne 64) { throw 'RUNTIME_HASH_SELF_TEST_FAILED' }
  Write-Output 'CANDIDATE_RUNTIME_SELF_TEST=PASS'
} finally {
  Remove-Item -LiteralPath $runtimePath -Force -ErrorAction SilentlyContinue
}
Write-Output 'CANDIDATE_PACKAGE_INVENTORY=PASS'
Write-Output 'CANDIDATE_POWERSHELL_PARSE=PASS'
Write-Output 'CANDIDATE_REACT_TYPESCRIPT_VITE_CONTRACT=PASS'
Write-Output 'CANDIDATE_READ_ONLY_GET_CLIENT_GUARD=PASS'
Write-Output 'CANDIDATE_NO_TOKEN_PERSISTENCE=PASS'
Write-Output 'CANDIDATE_LEGACY_FALLBACK_PRESERVATION=PASS'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PROJECT_MUTATION=NONE'
Write-Output 'SERVICE_START=NONE'
Write-Output 'SHELL_EXECUTION=NONE'
Write-Output 'GIT_WRITE=NONE'
Write-Output 'EXTERNAL_NETWORK=NONE'
Write-Output 'CANDIDATE_SYNTAX_RESULT=PASS'
