[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $PackageRoot).Path
$scripts = @(Get-ChildItem -LiteralPath (Join-Path $root 'scripts') -File -Filter '*.ps1')
$failures = @()

foreach ($script in $scripts) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile(
    $script.FullName,
    [ref]$tokens,
    [ref]$errors
  )
  foreach ($error in $errors) {
    $failures += "$($script.Name):$($error.Message)"
  }
}

$required = @(
  'backend\src\palwakf_local_agents\command_center\__init__.py',
  'backend\src\palwakf_local_agents\command_center\models.py',
  'backend\src\palwakf_local_agents\command_center\read_only_store.py',
  'backend\src\palwakf_local_agents\command_center\router.py',
  'backend\src\palwakf_local_agents\command_center\static\index.html',
  'backend\src\palwakf_local_agents\command_center\static\styles.css',
  'backend\src\palwakf_local_agents\command_center\static\app.js',
  'backend\tests\test_command_center_read_only.py',
  'scripts\Test-CommandCenterV1RevBStatic.ps1',
  'scripts\Install-CommandCenterV1RevB.ps1'
)

$missing = @(
  $required | Where-Object {
    -not (Test-Path -LiteralPath (Join-Path $root $_) -PathType Leaf)
  }
)

"PACKAGE_SCRIPT_COUNT=$($scripts.Count)"
"POWERSHELL_PARSE_FAILURE_COUNT=$($failures.Count)"
"POWERSHELL_PARSE_FAILURES=$($failures -join ';')"
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$($missing -join ';')"
"PACKAGE_LAYOUT=BACKEND_PACKAGE_NATIVE"
"ROOT_COMMAND_CENTER_OVERLAY=NOT_USED"
"MODEL_EXECUTION=NONE"
"PLATFORM_MUTATION=NONE"
"DATABASE_ACCESS=NONE"
"GIT_WRITE=NONE"
"DEPLOYMENT=NONE"
"SECRETS_ACCESS=NONE"
"MEMORY_WRITE=NONE"

if ($failures.Count -gt 0 -or $missing.Count -gt 0) {
  'SYNTAX_GATE_RESULT=FAIL'
  exit 1
}

'SYNTAX_GATE_RESULT=PASS'
