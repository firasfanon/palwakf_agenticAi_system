[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
$app=Join-Path $project 'backend\src\palwakf_local_agents\app.py'
$cc=Join-Path $project 'backend\src\palwakf_local_agents\command_center\router.py'
$failures=@()
foreach($path in @($app,$cc)){if(-not(Test-Path -LiteralPath $path -PathType Leaf)){$failures+="REQUIRED_TARGET_MISSING=$path"}}
$appText=if(Test-Path $app){Get-Content -LiteralPath $app -Raw -Encoding UTF8}else{''}
foreach($needle in @('from .command_center import mount_command_center','mount_command_center(app, project_root=PROJECT_ROOT)','PROJECT_ROOT = Path(__file__).resolve().parents[3]')){if($appText -notmatch [regex]::Escape($needle)){$failures+="COMMAND_CENTER_BASELINE_TOKEN_MISSING=$needle"}}
if($appText -match [regex]::Escape('from .governed_operations import mount_governed_operations')){$failures+='GOVERNED_OPERATIONS_IMPORT_ALREADY_PRESENT'}
if($appText -match [regex]::Escape('mount_governed_operations(app, project_root=PROJECT_ROOT)')){$failures+='GOVERNED_OPERATIONS_MOUNT_ALREADY_PRESENT'}
Write-Output "PREFLIGHT_FAILURE_COUNT=$($failures.Count)";Write-Output "PREFLIGHT_FAILURES=$($failures -join ';')";Write-Output 'COMMAND_CENTER_READ_ONLY_SURFACE=REQUIRED_EXISTING_BASELINE';Write-Output 'PATCH_SCOPE=NEW_GOVERNED_OPERATIONS_MODULE_PLUS_EXPLICIT_MOUNT';Write-Output 'APP_ENTRYPOINT_MUTATION=PLANNED_EXPLICIT_GOVERNED_OPERATIONS_MOUNT_ONLY';Write-Output 'COMMAND_CENTER_STATIC_MUTATION=NONE';Write-Output 'MODEL_EXECUTION=NONE';Write-Output 'PILOT_EXECUTION=NOT_EXECUTED';Write-Output 'PLATFORM_MUTATION=NONE';Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE';Write-Output 'LOCAL_PERSISTENT_STATE=PLANNED_SQLITE_ONLY'
if($failures.Count){Write-Output 'PREFLIGHT_RESULT=FAIL';exit 1};Write-Output 'PREFLIGHT_RESULT=PASS'
