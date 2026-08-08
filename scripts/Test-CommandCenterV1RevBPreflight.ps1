[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$appPath = Join-Path $root 'backend\src\palwakf_local_agents\app.py'
$pyproject = Join-Path $root 'pyproject.toml'
$legacyRoot = Join-Path $root 'command_center'
$approvedTask = Join-Path $root 'tasks\approved\SAPF_DOCUMENTATION_HANDOFF_PILOT_001.json'
$failures = @()

foreach ($path in @($appPath, $pyproject, $approvedTask)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    $failures += "REQUIRED_BASELINE_FILE_MISSING=$path"
  }
}

if ($failures.Count -eq 0) {
  $app = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
  if ($app -match 'mount_command_center|from \.command_center import') {
    $failures += 'APP_ENTRYPOINT_ALREADY_HAS_COMMAND_CENTER_MOUNT'
  }
}

"REQUIRED_BASELINE_FILE_COUNT=3"
"PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
"PREFLIGHT_FAILURES=$($failures -join ';')"
"LEGACY_ROOT_COMMAND_CENTER_PRESENT=$([bool](Test-Path -LiteralPath $legacyRoot -PathType Container))"
"LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED"
"TARGET_PACKAGE_LOCATION=backend/src/palwakf_local_agents/command_center"
"TARGET_TEST_LOCATION=backend/tests/test_command_center_read_only.py"
"APP_ENTRYPOINT_MUTATION=EXPLICIT_MOUNT_ONLY"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PLATFORM_MUTATION=NONE"
"DATABASE_ACCESS=NONE"
"GIT_WRITE=NONE"
"DEPLOYMENT=NONE"
"SECRETS_ACCESS=NONE"
"MEMORY_WRITE=NONE"

if ($failures.Count -gt 0) {
  'PREFLIGHT_RESULT=FAIL'
  exit 1
}

'PREFLIGHT_RESULT=PASS'
