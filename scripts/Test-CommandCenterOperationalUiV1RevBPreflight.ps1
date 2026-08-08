[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot)
$ErrorActionPreference = "Stop"
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
$staticRoot = Join-Path $project "backend\src\palwakf_local_agents\command_center\static"
$router = Join-Path $project "backend\src\palwakf_local_agents\command_center\router.py"
$app = Join-Path $project "backend\src\palwakf_local_agents\app.py"
$store = Join-Path $project "backend\src\palwakf_local_agents\command_center\read_only_store.py"

$failures = @()
foreach ($path in @(
  (Join-Path $staticRoot "index.html"),
  (Join-Path $staticRoot "styles.css"),
  (Join-Path $staticRoot "app.js"),
  $router, $app, $store
)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    $failures += "TARGET_FILE_NOT_FOUND=$path"
  }
}

$routerText = if (Test-Path -LiteralPath $router) { Get-Content -LiteralPath $router -Raw -Encoding UTF8 } else { "" }
foreach ($token in @(
  'StaticFiles(directory=STATIC_ROOT)',
  '@api.get("/dashboard")',
  '@api.get("/system-health")',
  '@app.get(ui_prefix'
)) {
  if ($routerText -notmatch [regex]::Escape($token)) {
    $failures += "ROUTER_CONTRACT_TOKEN_MISSING=$token"
  }
}

$appText = if (Test-Path -LiteralPath $app) { Get-Content -LiteralPath $app -Raw -Encoding UTF8 } else { "" }
if ($appText -notmatch [regex]::Escape('mount_command_center(app, project_root=PROJECT_ROOT)')) {
  $failures += "APP_MOUNT_TOKEN_MISSING"
}

Write-Output "PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
Write-Output "PREFLIGHT_FAILURES=$($failures -join ';')"
Write-Output "UI_TARGET_ROOT=backend/src/palwakf_local_agents/command_center/static"
Write-Output "PATCH_SCOPE=STATIC_ASSETS_ONLY"
Write-Output "APP_ENTRYPOINT_MUTATION=NONE"
Write-Output "ROUTER_MUTATION=NONE"
Write-Output "STORE_MUTATION=NONE"
Write-Output "API_MUTATION=NONE"
Write-Output "TASK_STATE_MUTATION=NONE"
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
