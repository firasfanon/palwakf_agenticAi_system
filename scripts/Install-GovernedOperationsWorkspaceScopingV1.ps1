[CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='High')]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$PackageRoot,[Parameter(Mandatory=$true)][string]$PreflightManifest,[ValidateSet('Upgrade')][string]$Mode='Upgrade',[switch]$Apply)
$ErrorActionPreference='Stop'
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
if(-not(Test-Path -LiteralPath $PreflightManifest -PathType Leaf)){throw "PREFLIGHT_MANIFEST_NOT_FOUND=$PreflightManifest"}
$manifest=Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8|ConvertFrom-Json
if($manifest.contract -ne 'GOVERNED_OPERATIONS_WORKSPACE_SCOPING_V1'){throw 'PREFLIGHT_MANIFEST_CONTRACT_MISMATCH'}
foreach($prop in $manifest.files.psobject.Properties){$path=Join-Path $ProjectRoot $prop.Name;if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "TARGET_MISSING_SINCE_PREFLIGHT=$($prop.Name)"};if((Hash $path) -ne $prop.Value){throw "TARGET_CHANGED_SINCE_PREFLIGHT=$($prop.Name)"}}
$targets=@(
 'backend/src/palwakf_local_agents/governed_operations/__init__.py',
 'backend/src/palwakf_local_agents/governed_operations/contracts.py',
 'backend/src/palwakf_local_agents/governed_operations/store.py',
 'backend/src/palwakf_local_agents/governed_operations/router.py',
 'backend/src/palwakf_local_agents/governed_operations/static/index.html',
 'backend/src/palwakf_local_agents/governed_operations/static/styles.css',
 'backend/src/palwakf_local_agents/governed_operations/static/app.js',
 'backend/tests/test_governed_operations_workspace_scoping.py'
)
if((-not $Apply) -or (-not $PSCmdlet.ShouldProcess($ProjectRoot, 'Apply Governed Operations Workspace Scoping V1'))){'INSTALL_STATUS=WHATIF_COMPLETE';'PROJECT_MUTATION=NONE';'LOCAL_SQLITE_WRITE=NONE';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';return}
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss';$backup=Join-Path $ProjectRoot "backups/governed_operations_workspace_scoping_v1_$stamp";New-Item -ItemType Directory -Path $backup -Force|Out-Null
$pre=@{}
foreach($relative in $targets){$source=Join-Path $PackageRoot $relative;$dest=Join-Path $ProjectRoot $relative;if(-not(Test-Path -LiteralPath $source -PathType Leaf)){throw "CANDIDATE_SOURCE_MISSING=$relative"};if(Test-Path -LiteralPath $dest -PathType Leaf){$pre[$relative]=Hash $dest;$b=Join-Path $backup $relative;New-Item -ItemType Directory -Path (Split-Path $b -Parent) -Force|Out-Null;Copy-Item -LiteralPath $dest -Destination $b -Force}}
[ordered]@{install='GOVERNED_OPERATIONS_WORKSPACE_SCOPING_V1';preimage=$pre}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $backup 'install_preimage_manifest.json') -Encoding UTF8
foreach($relative in $targets){$source=Join-Path $PackageRoot $relative;$dest=Join-Path $ProjectRoot $relative;New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force|Out-Null;Copy-Item -LiteralPath $source -Destination $dest -Force}
'INSTALL_STATUS=COMPLETE'
"BACKUP_PATH=$backup"
'TARGET_MUTATION_SCOPE=GOVERNED_OPERATIONS_MODULE_AND_SCOPED_TEST_ONLY'
'APP_ENTRYPOINT_MUTATION=NONE'
'WORKSPACE_CORE_SOURCE_MUTATION=NONE'
'POLICY_PACK_MUTATION=NONE'
'COMMAND_CENTER_MUTATION=NONE'
'LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL'
'LEGACY_GOVERNED_OPERATIONS_MIGRATION=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
