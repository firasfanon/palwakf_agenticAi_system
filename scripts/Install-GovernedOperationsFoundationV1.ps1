[CmdletBinding(SupportsShouldProcess=$true)]
param(
 [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
 [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
 [ValidateSet('Upgrade')][string]$Mode='Upgrade'
)
$ErrorActionPreference='Stop'
$package=(Resolve-Path -LiteralPath $PackageRoot).Path
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
function Write-Utf8NoBom{param([string]$Path,[string]$Content)$dir=Split-Path -Parent $Path;if(-not(Test-Path $dir)){New-Item -ItemType Directory -Path $dir -Force|Out-Null};$utf8=New-Object System.Text.UTF8Encoding($false);[System.IO.File]::WriteAllText($Path,$Content,$utf8)}
function HashOrEmpty{param([string]$Path)if(Test-Path -LiteralPath $Path -PathType Leaf){return(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash};return''}
$appRel='backend\src\palwakf_local_agents\app.py';$appPath=Join-Path $project $appRel
$files=@(
 'backend\src\palwakf_local_agents\governed_operations\__init__.py',
 'backend\src\palwakf_local_agents\governed_operations\contracts.py',
 'backend\src\palwakf_local_agents\governed_operations\store.py',
 'backend\src\palwakf_local_agents\governed_operations\router.py',
 'backend\src\palwakf_local_agents\governed_operations\static\index.html',
 'backend\src\palwakf_local_agents\governed_operations\static\styles.css',
 'backend\src\palwakf_local_agents\governed_operations\static\app.js',
 'backend\tests\test_governed_operations.py',
 'docs\ARCHITECTURE_GOVERNED_OPERATIONS_FOUNDATION_V1_AR.md',
 'docs\SECURITY_CONTRACT_GOVERNED_OPERATIONS_FOUNDATION_V1.md',
 'docs\UAT_GOVERNED_OPERATIONS_FOUNDATION_V1_AR.md',
 'docs\CHANGELOG_GOVERNED_OPERATIONS_FOUNDATION_V1.md'
)
foreach($rel in $files){if(-not(Test-Path -LiteralPath (Join-Path $package $rel) -PathType Leaf)){throw "PACKAGE_FILE_MISSING=$rel"}}
if(-not(Test-Path -LiteralPath $appPath -PathType Leaf)){throw "APP_ENTRYPOINT_MISSING=$appPath"}
$appText=Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
if($appText -notmatch [regex]::Escape('from .command_center import mount_command_center')){throw 'COMMAND_CENTER_IMPORT_ANCHOR_MISSING'}
if($appText -notmatch [regex]::Escape('mount_command_center(app, project_root=PROJECT_ROOT)')){throw 'COMMAND_CENTER_MOUNT_ANCHOR_MISSING'}
if($appText -match [regex]::Escape('from .governed_operations import mount_governed_operations')){throw 'GOVERNED_OPERATIONS_IMPORT_ALREADY_PRESENT'}
if($appText -match [regex]::Escape('mount_governed_operations(app, project_root=PROJECT_ROOT)')){throw 'GOVERNED_OPERATIONS_MOUNT_ALREADY_PRESENT'}
$patched=$appText -replace [regex]::Escape('from .command_center import mount_command_center'), "from .command_center import mount_command_center`r`nfrom .governed_operations import mount_governed_operations"
$patched=$patched -replace [regex]::Escape('mount_command_center(app, project_root=PROJECT_ROOT)'), "mount_command_center(app, project_root=PROJECT_ROOT)`r`nmount_governed_operations(app, project_root=PROJECT_ROOT)"
$stamp=Get-Date -Format 'yyyyMMddHHmmss';$backup=Join-Path $project "backups\governed_operations_foundation_v1_$stamp";$manifest=Join-Path $backup 'install_preimage_manifest.json';$plan=@($appRel)+$files
if($WhatIfPreference){foreach($r in $plan){$target=Join-Path $project $r;$dest=Join-Path $backup (Join-Path 'preimage' $r);if($PSCmdlet.ShouldProcess($dest,'Backup governed operations preimage')){Copy-Item -LiteralPath $target -Destination $dest -Force};if($r -ne $appRel -and $PSCmdlet.ShouldProcess((Join-Path $project $r),'Install governed operations file')){Copy-Item -LiteralPath (Join-Path $package $r) -Destination (Join-Path $project $r) -Force}};Write-Output 'INSTALL_STATUS=WHATIF_COMPLETE';Write-Output "BACKUP_PATH=$backup";Write-Output "BACKUP_MANIFEST_PATH=$manifest";Write-Output 'BACKUP_STATUS=PLANNED';Write-Output 'INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY';Write-Output 'APP_ENTRYPOINT_MUTATION=PLANNED_EXPLICIT_GOVERNED_OPERATIONS_MOUNT_ONLY';Write-Output 'COMMAND_CENTER_READ_ONLY_SURFACE=UNCHANGED';Write-Output 'MODEL_EXECUTION=NONE';Write-Output 'PILOT_EXECUTION=NOT_EXECUTED';Write-Output 'PLATFORM_MUTATION=NONE';Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE';Write-Output 'LOCAL_PERSISTENT_STATE=PLANNED_SQLITE_ONLY';exit 0}
New-Item -ItemType Directory -Path $backup -Force|Out-Null;$pre=@();foreach($r in $plan){$target=Join-Path $project $r;$exists=Test-Path -LiteralPath $target -PathType Leaf;$brel=if($exists){Join-Path 'preimage' $r}else{''};if($exists){$bpath=Join-Path $backup $brel;New-Item -ItemType Directory -Path (Split-Path -Parent $bpath) -Force|Out-Null;Copy-Item -LiteralPath $target -Destination $bpath -Force};$pre+=[ordered]@{relative_path=$r;existed_before=[bool]$exists;sha256_before=HashOrEmpty $target;backup_relative_path=$brel}}
$meta=[ordered]@{package='MEGA_BATCH_LOCAL_AGENTS_GOVERNED_OPERATIONS_FOUNDATION_V1';install_mode=$Mode;created_at_local=(Get-Date).ToString('o');backup_path=$backup;preimages=$pre;safety_posture=[ordered]@{MODEL_EXECUTION='NONE';PILOT_EXECUTION='NOT_EXECUTED';PLATFORM_MUTATION='NONE';EXTERNAL_DATABASE_ACCESS='NONE';GIT_WRITE='NONE';DEPLOYMENT='NONE';SECRETS_ACCESS='NONE';MEMORY_WRITE='NONE';LOCAL_PERSISTENT_STATE='SQLITE_ONLY'}};Write-Utf8NoBom $manifest ($meta|ConvertTo-Json -Depth 15)
Write-Utf8NoBom $appPath $patched
foreach($r in $files){$source=Join-Path $package $r;$target=Join-Path $project $r;New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force|Out-Null;Copy-Item -LiteralPath $source -Destination $target -Force}
$post=@();foreach($r in $plan){$post+=[ordered]@{relative_path=$r;sha256_after=HashOrEmpty (Join-Path $project $r)}};$meta.postinstall=$post;$meta.install_status='COMPLETE';$meta.completed_at_local=(Get-Date).ToString('o');Write-Utf8NoBom $manifest ($meta|ConvertTo-Json -Depth 15)
Write-Output 'INSTALL_STATUS=COMPLETE';Write-Output "BACKUP_PATH=$backup";Write-Output "BACKUP_MANIFEST_PATH=$manifest";Write-Output 'BACKUP_STATUS=COMPLETE';Write-Output 'INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY';Write-Output 'APP_ENTRYPOINT_MUTATION=EXPLICIT_GOVERNED_OPERATIONS_MOUNT_ONLY';Write-Output 'COMMAND_CENTER_READ_ONLY_SURFACE=UNCHANGED';Write-Output 'LOCAL_OPERATIONS_API=LOCAL_STATE_WRITES_ONLY';Write-Output 'LOCAL_PERSISTENT_STATE=SQLITE_ONLY';Write-Output 'MODEL_EXECUTION=NONE';Write-Output 'PILOT_EXECUTION=NOT_EXECUTED';Write-Output 'PLATFORM_MUTATION=NONE';Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE';Write-Output 'GIT_WRITE=NONE';Write-Output 'DEPLOYMENT=NONE';Write-Output 'SECRETS_ACCESS=NONE';Write-Output 'MEMORY_WRITE=NONE';Write-Output 'NEXT_STEP=RUN_GOVERNED_OPERATIONS_TESTS_AND_LOCAL_UAT'
