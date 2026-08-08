[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot)
$ErrorActionPreference = "Stop"
$p = (Resolve-Path -LiteralPath $PackageRoot).Path

$required = @(
  "static\index.html",
  "static\styles.css",
  "static\app.js",
  "scripts\Test-CommandCenterOperationalUiV1RevBSyntax.ps1",
  "scripts\Test-CommandCenterOperationalUiV1RevBPreflight.ps1",
  "scripts\Test-CommandCenterOperationalUiV1RevBStaticEval.ps1",
  "scripts\Install-CommandCenterOperationalUiV1RevB.ps1",
  "docs\README_OPERATIONAL_UI_UX_READ_ONLY_V1_REVB_AR.md",
  "docs\SECURITY_CONTRACT_OPERATIONAL_UI_UX_READ_ONLY_V1.md",
  "docs\UAT_OPERATIONAL_UI_UX_READ_ONLY_V1_AR.md",
  "MANIFEST_OPERATIONAL_UI_UX_READ_ONLY_V1_REVB.md"
)

$missing = @()
foreach ($rel in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $p $rel) -PathType Leaf)) {
    $missing += $rel
  }
}

$parseFailures = @()
Get-ChildItem -LiteralPath (Join-Path $p "scripts") -Filter "*.ps1" -File | ForEach-Object {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$errors)
  foreach ($err in $errors) {
    $parseFailures += "$($_.Name):$($err.Extent.StartLineNumber):$($err.Message)"
  }
}

$html = Get-Content -LiteralPath (Join-Path $p "static\index.html") -Raw -Encoding UTF8
$js = Get-Content -LiteralPath (Join-Path $p "static\app.js") -Raw -Encoding UTF8
$css = Get-Content -LiteralPath (Join-Path $p "static\styles.css") -Raw -Encoding UTF8

$markerFailures = @()
foreach ($needle in @(
  'lang="ar" dir="rtl"',
  'READ_ONLY_OPERATIONAL_DASHBOARD',
  '/api/v1/local-agents',
  '/system-health',
  '/governance'
)) {
  if (($html + $js + $css) -notmatch [regex]::Escape($needle)) {
    $markerFailures += $needle
  }
}

$forbidden = @()
if ($js -match '(?i)\bmethod\s*:\s*[''"](?:POST|PUT|PATCH|DELETE)[''"]') {
  $forbidden += "WEB_NON_GET_METHOD"
}
if ($js -match '(?i)\b(localStorage|sessionStorage)\.(setItem|removeItem|clear)\s*\(') {
  $forbidden += "BROWSER_PERSISTENCE_WRITE"
}

Write-Output "REQUIRED_FILE_COUNT=$($required.Count)"
Write-Output "MISSING_FILE_COUNT=$($missing.Count)"
Write-Output "MISSING_FILES=$($missing -join ';')"
Write-Output "POWERSHELL_PARSE_FAILURE_COUNT=$($parseFailures.Count)"
Write-Output "POWERSHELL_PARSE_FAILURES=$($parseFailures -join ';')"
Write-Output "UI_MARKER_FAILURE_COUNT=$($markerFailures.Count)"
Write-Output "UI_MARKER_FAILURES=$($markerFailures -join ';')"
Write-Output "FORBIDDEN_UI_PATTERN_COUNT=$($forbidden.Count)"
Write-Output "FORBIDDEN_UI_PATTERNS=$($forbidden -join ';')"
Write-Output "UI_SCOPE=STATIC_ASSETS_ONLY"
Write-Output "UI_LANGUAGE=ARABIC_RTL"
Write-Output "UI_MODE=READ_ONLY_OPERATIONAL_DASHBOARD"
Write-Output "SCRIPT_ENCODING_GATE=ASCII_MARKERS_ONLY"
Write-Output "RESPONSIVE_EVAL_REGEX=WHITESPACE_TOLERANT"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"

if ($missing.Count -gt 0 -or $parseFailures.Count -gt 0 -or $markerFailures.Count -gt 0 -or $forbidden.Count -gt 0) {
  Write-Output "SYNTAX_GATE_RESULT=FAIL"
  exit 1
}
Write-Output "SYNTAX_GATE_RESULT=PASS"
exit 0
