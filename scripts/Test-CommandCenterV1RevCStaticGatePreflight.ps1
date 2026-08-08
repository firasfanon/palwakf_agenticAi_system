[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path

$targetStaticGate = Join-Path $root "scripts\Test-CommandCenterV1RevBStatic.ps1"
$appEntry = Join-Path $root "backend\src\palwakf_local_agents\app.py"
$commandCenterRoot = Join-Path $root "backend\src\palwakf_local_agents\command_center"
$legacyRoot = Join-Path $root "command_center"

$failures = @()

foreach ($path in @($targetStaticGate, $appEntry)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures += "REQUIRED_TARGET_FILE_MISSING=$path"
    }
}

if (-not (Test-Path -LiteralPath $commandCenterRoot -PathType Container)) {
    $failures += "COMMAND_CENTER_PACKAGE_MISSING=$commandCenterRoot"
}

$appText = if (Test-Path -LiteralPath $appEntry -PathType Leaf) {
    Get-Content -LiteralPath $appEntry -Raw -Encoding UTF8
} else {
    ""
}
foreach ($token in @(
    "from .command_center import mount_command_center",
    "PROJECT_ROOT",
    "mount_command_center"
)) {
    if ($appText -notmatch [regex]::Escape($token)) {
        $failures += "APP_INTEGRATION_TOKEN_MISSING=$token"
    }
}

Write-Output "PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
Write-Output "PREFLIGHT_FAILURES=$($failures -join ';')"
Write-Output "TARGET_STATIC_GATE=$targetStaticGate"
Write-Output "COMMAND_CENTER_PACKAGE_LOCATION=backend/src/palwakf_local_agents/command_center"
Write-Output "LEGACY_ROOT_COMMAND_CENTER_PRESENT=$([bool](Test-Path -LiteralPath $legacyRoot))"
Write-Output "LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED"
Write-Output "PATCH_SCOPE=STATIC_GATE_ONLY"
Write-Output "CORE_RUNTIME_MUTATION=NONE"
Write-Output "CORE_11_LINE_CONTRACT_MUTATION=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "DEPLOYMENT=NONE"
Write-Output "SECRETS_ACCESS=NONE"
Write-Output "MEMORY_WRITE=NONE"

if ($failures.Count -gt 0) {
    Write-Output "PREFLIGHT_RESULT=FAIL"
    exit 1
}

Write-Output "PREFLIGHT_RESULT=PASS"
exit 0
