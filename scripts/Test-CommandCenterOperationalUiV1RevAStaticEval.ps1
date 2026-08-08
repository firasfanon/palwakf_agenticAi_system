[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot)
$ErrorActionPreference = "Stop"
$p = (Resolve-Path -LiteralPath $PackageRoot).Path
$html = Get-Content -LiteralPath (Join-Path $p "static\index.html") -Raw -Encoding UTF8
$js = Get-Content -LiteralPath (Join-Path $p "static\app.js") -Raw -Encoding UTF8
$css = Get-Content -LiteralPath (Join-Path $p "static\styles.css") -Raw -Encoding UTF8

$checks = @(
  @{name="RTL_DOCUMENT"; value=($html -match 'lang="ar"\s+dir="rtl"')},
  @{name="READ_ONLY_ASCII_CONTRACT"; value=(($html + $js) -match [regex]::Escape('READ_ONLY_OPERATIONAL_DASHBOARD'))},
  @{name="CORE_GET_SURFACES"; value=($js -match '/dashboard' -and $js -match '/tasks' -and $js -match '/reviews' -and $js -match '/evidence' -and $js -match '/agents' -and $js -match '/governance' -and $js -match '/system-health')},
  @{name="NO_NON_GET_METHOD"; value=(-not ($js -match '(?i)\bmethod\s*:\s*[''"](?:POST|PUT|PATCH|DELETE)[''"]'))},
  @{name="NO_BROWSER_STORAGE_WRITE"; value=(-not ($js -match '(?i)\b(localStorage|sessionStorage)\.(setItem|removeItem|clear)\s*\('))},
  @{name="RESPONSIVE_BREAKPOINTS"; value=($css -match '@media \(max-width: 900px\)' -and $css -match '@media \(max-width: 620px\)')},
  @{name="DARK_OPERATIONAL_THEME"; value=($css -match '--bg:' -and $css -match '--blue:' -and $css -match '--purple:')}
)

$failures = @($checks | Where-Object { -not $_.value } | ForEach-Object { $_.name })
$passCount = $checks.Count - $failures.Count

Write-Output "EVAL_CASE_COUNT=$($checks.Count)"
Write-Output "EVAL_PASSED_COUNT=$passCount"
Write-Output "EVAL_FAILED_COUNT=$($failures.Count)"
Write-Output "EVAL_FAILURES=$($failures -join ';')"
Write-Output "EVAL_SCOPE=STATIC_UI_READ_ONLY_CONTRACT"
Write-Output "SCRIPT_ENCODING_GATE=ASCII_MARKERS_ONLY"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"

if ($failures.Count -gt 0) {
  Write-Output "EVAL_RESULT=FAIL"
  exit 1
}
Write-Output "EVAL_RESULT=PASS"
exit 0
