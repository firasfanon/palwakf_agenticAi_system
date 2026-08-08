[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot,
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
  [ValidateSet('Upgrade')][string]$Mode='Upgrade'
)
$ErrorActionPreference='Stop'
$package=(Resolve-Path -LiteralPath $PackageRoot).Path
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
$relative='backend\src\palwakf_local_agents\governed_operations\static\app.js'
$source=Join-Path $package $relative
$target=Join-Path $project $relative
$expectedPre='49B69C3936DE0DFC653FA2D0FD15BB848C17646B8F3DACA6B56E8249EFA9FD7A'
$expectedPost='9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041'
function Write-Utf8NoBom{param([string]$Path,[string]$Content)$dir=Split-Path -Parent $Path;if(-not(Test-Path -LiteralPath $dir)){New-Item -ItemType Directory -Path $dir -Force|Out-Null};$utf8=New-Object System.Text.UTF8Encoding($false);[System.IO.File]::WriteAllText($Path,$Content,$utf8)}
function HashOf{param([string]$Path) return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
function SplitCounts{param([string]$Path)$t=Get-Content -LiteralPath $Path -Raw -Encoding UTF8;return [ordered]@{malformed=[regex]::Matches($t,'\.split\("(\r?\n)"\)').Count;fixed=[regex]::Matches($t,'\.split\("\\n"\)').Count}}
foreach($p in @($source,$target)){if(-not(Test-Path -LiteralPath $p -PathType Leaf)){throw "REQUIRED_APP_JS_PATH_MISSING=$p"}}
$node=Get-Command node -ErrorAction SilentlyContinue
if($null -eq $node){throw 'NODE_NOT_FOUND'}
& $node.Source --check $source
if($LASTEXITCODE -ne 0){throw "CANDIDATE_NODE_CHECK_FAILED=$LASTEXITCODE"}
$preHash=HashOf $target
$preCounts=SplitCounts $target
if($preHash -ne $expectedPre){throw "UNEXPECTED_PREIMAGE_SHA256=$preHash"}
if($preCounts.malformed -ne 1 -or $preCounts.fixed -ne 0){throw "UNEXPECTED_PREIMAGE_SPLIT_STATE=malformed:$($preCounts.malformed);fixed:$($preCounts.fixed)"}
if((HashOf $source) -ne $expectedPost){throw 'CANDIDATE_POSTIMAGE_HASH_MISMATCH'}
$stamp=Get-Date -Format 'yyyyMMddHHmmss'
$backup=Join-Path $project "backups\governed_operations_browser_js_syntax_closure_v1_$stamp"
$manifest=Join-Path $backup 'install_preimage_manifest.json'
if($WhatIfPreference){
  $backupFile=Join-Path $backup (Join-Path 'preimage' $relative)
  if($PSCmdlet.ShouldProcess($backupFile,'Backup governed operations app.js preimage')){Copy-Item -LiteralPath $target -Destination $backupFile -Force}
  if($PSCmdlet.ShouldProcess($target,'Install governed operations app.js syntax closure')){Copy-Item -LiteralPath $source -Destination $target -Force}
  Write-Output 'INSTALL_STATUS=WHATIF_COMPLETE'
  Write-Output "BACKUP_PATH=$backup"
  Write-Output "BACKUP_MANIFEST_PATH=$manifest"
  Write-Output 'BACKUP_STATUS=PLANNED'
  Write-Output 'INSTALL_BACKUP_STRATEGY=EXACT_SINGLE_FILE_PREIMAGE_COPY'
  Write-Output 'TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY'
  Write-Output 'TARGET_MUTATED_FILE=backend/src/palwakf_local_agents/governed_operations/static/app.js'
  Write-Output 'APP_ENTRYPOINT_MUTATION=NONE'
  Write-Output 'ROUTER_MUTATION=NONE'
  Write-Output 'STORE_MUTATION=NONE'
  Write-Output 'COMMAND_CENTER_MUTATION=NONE'
  Write-Output 'LOCAL_SQLITE_WRITE=NONE'
  Write-Output 'MODEL_EXECUTION=NONE'
  Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
  Write-Output 'PLATFORM_MUTATION=NONE'
  Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE'
  exit 0
}
New-Item -ItemType Directory -Path $backup -Force|Out-Null
$backupFile=Join-Path $backup (Join-Path 'preimage' $relative)
New-Item -ItemType Directory -Path (Split-Path -Parent $backupFile) -Force|Out-Null
Copy-Item -LiteralPath $target -Destination $backupFile -Force
$meta=[ordered]@{package='GOVERNED_OPERATIONS_BROWSER_JS_SYNTAX_CLOSURE_V1';install_mode=$Mode;created_at_local=(Get-Date).ToString('o');backup_path=$backup;target_relative_path=$relative;preimage_sha256=$preHash;preimage_malformed_split_count=$preCounts.malformed;preimage_fixed_split_count=$preCounts.fixed;backup_relative_path=(Join-Path 'preimage' $relative);safety_posture=[ordered]@{MODEL_EXECUTION='NONE';PILOT_EXECUTION='NOT_EXECUTED';PLATFORM_MUTATION='NONE';EXTERNAL_DATABASE_ACCESS='NONE';GIT_WRITE='NONE';DEPLOYMENT='NONE';SECRETS_ACCESS='NONE';MEMORY_WRITE='NONE';LOCAL_SQLITE_WRITE='NONE'}}
Write-Utf8NoBom $manifest ($meta|ConvertTo-Json -Depth 10)
Copy-Item -LiteralPath $source -Destination $target -Force
$postHash=HashOf $target
$postCounts=SplitCounts $target
if($postHash -ne $expectedPost){throw "POSTIMAGE_SHA256_MISMATCH=$postHash"}
if($postCounts.malformed -ne 0 -or $postCounts.fixed -lt 1){throw "POSTIMAGE_SPLIT_STATE_UNEXPECTED=malformed:$($postCounts.malformed);fixed:$($postCounts.fixed)"}
& $node.Source --check $target
if($LASTEXITCODE -ne 0){throw "TARGET_NODE_CHECK_FAILED=$LASTEXITCODE"}
$meta.postimage_sha256=$postHash;$meta.postimage_malformed_split_count=$postCounts.malformed;$meta.postimage_fixed_split_count=$postCounts.fixed;$meta.install_status='COMPLETE';$meta.completed_at_local=(Get-Date).ToString('o');Write-Utf8NoBom $manifest ($meta|ConvertTo-Json -Depth 10)
Write-Output 'INSTALL_STATUS=COMPLETE'
Write-Output "BACKUP_PATH=$backup"
Write-Output "BACKUP_MANIFEST_PATH=$manifest"
Write-Output 'BACKUP_STATUS=COMPLETE'
Write-Output 'INSTALL_BACKUP_STRATEGY=EXACT_SINGLE_FILE_PREIMAGE_COPY'
Write-Output 'TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY'
Write-Output 'TARGET_MUTATED_FILE=backend/src/palwakf_local_agents/governed_operations/static/app.js'
Write-Output 'APP_ENTRYPOINT_MUTATION=NONE'
Write-Output 'ROUTER_MUTATION=NONE'
Write-Output 'STORE_MUTATION=NONE'
Write-Output 'COMMAND_CENTER_MUTATION=NONE'
Write-Output 'LOCAL_SQLITE_WRITE=NONE'
Write-Output 'MALFORMED_SPLIT_LITERAL=REMOVED'
Write-Output 'NODE_CHECK_TARGET=PASS'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PLATFORM_MUTATION=NONE'
Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE'
Write-Output 'GIT_WRITE=NONE'
Write-Output 'DEPLOYMENT=NONE'
Write-Output 'SECRETS_ACCESS=NONE'
Write-Output 'MEMORY_WRITE=NONE'
Write-Output 'NEXT_STEP=RUN_POST_APPLY_STATIC_GATE_AND_BROWSER_UAT'
