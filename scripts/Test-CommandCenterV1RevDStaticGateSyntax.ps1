[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PackageRoot
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $PackageRoot).Path

$requiredFiles = @(
    "scripts\Test-CommandCenterV1RevBStatic.ps1",
    "scripts\Test-CommandCenterV1RevDStaticGateSyntax.ps1",
    "scripts\Test-CommandCenterV1RevDStaticGatePreflight.ps1",
    "scripts\Test-CommandCenterV1RevDStaticGateEval.ps1",
    "scripts\Install-CommandCenterV1RevDStaticGatePrecisionHotfix.ps1",
    "README_COMMAND_CENTER_V1_2_REVD_AR.md",
    "APPLY_GUIDE_COMMAND_CENTER_V1_2_REVD_AR.md",
    "COMMAND_CENTER_V1_2_REVD_SECURITY_CONTRACT.md",
    "ERROR_RECORD_COMMAND_CENTER_V1_2_REVD_AR.md",
    "MANIFEST_COMMAND_CENTER_V1_2_REVD_CANDIDATE.md"
)

$missingFiles = @()
foreach ($relativePath in $requiredFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $relativePath) -PathType Leaf)) {
        $missingFiles += $relativePath
    }
}

$parseFailures = @()
$scriptFiles = Get-ChildItem -LiteralPath (Join-Path $root "scripts") -Filter "*.ps1" -File
foreach ($scriptFile in $scriptFiles) {
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $scriptFile.FullName,
        [ref]$tokens,
        [ref]$errors
    )
    foreach ($error in $errors) {
        $parseFailures += "$($scriptFile.Name):$($error.Extent.StartLineNumber):$($error.Message)"
    }
}

$gatePath = Join-Path $root "scripts\Test-CommandCenterV1RevBStatic.ps1"
$gateText = Get-Content -LiteralPath $gatePath -Raw -Encoding UTF8
$requiredMarkers = @(
    "GENERIC_STRING_REPLACE_TREATMENT=NON_MUTATING_EXCLUDED",
    "FILE_MUTATION_SCAN_SCOPE=PYTHON_FILESYSTEM_OPERATIONS_ONLY",
    "WEB_NON_GET_METHOD_SCAN=ACTIVE",
    "PY_CACHE_EXCLUSION=ACTIVE"
)
$markerFailures = @()
foreach ($marker in $requiredMarkers) {
    if ($gateText -notmatch [regex]::Escape($marker)) {
        $markerFailures += $marker
    }
}

Write-Output "PACKAGE_SCRIPT_COUNT=$($scriptFiles.Count)"
Write-Output "POWERSHELL_PARSE_FAILURE_COUNT=$($parseFailures.Count)"
Write-Output "POWERSHELL_PARSE_FAILURES=$($parseFailures -join ';')"
Write-Output "REQUIRED_FILE_COUNT=$($requiredFiles.Count)"
Write-Output "MISSING_FILE_COUNT=$($missingFiles.Count)"
Write-Output "MISSING_FILES=$($missingFiles -join ';')"
Write-Output "STATIC_GATE_MARKER_FAILURE_COUNT=$($markerFailures.Count)"
Write-Output "STATIC_GATE_MARKER_FAILURES=$($markerFailures -join ';')"
Write-Output "SCOPE=STATIC_GATE_PRECISION_HOTFIX_ONLY"
Write-Output "CORE_RUNTIME_MUTATION=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"

if ($parseFailures.Count -gt 0 -or $missingFiles.Count -gt 0 -or $markerFailures.Count -gt 0) {
    Write-Output "SYNTAX_GATE_RESULT=FAIL"
    exit 1
}

Write-Output "SYNTAX_GATE_RESULT=PASS"
exit 0
