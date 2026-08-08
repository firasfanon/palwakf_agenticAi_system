[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
'backend\src\palwakf_local_agents\workspace_core\__init__.py',
'backend\src\palwakf_local_agents\workspace_core\policy.py',
'backend\src\palwakf_local_agents\workspace_core\store.py',
'backend\src\palwakf_local_agents\workspace_core\router.py',
'backend\src\palwakf_local_agents\workspace_core\static\index.html',
'backend\src\palwakf_local_agents\workspace_core\static\styles.css',
'backend\src\palwakf_local_agents\workspace_core\static\app.js',
'backend\tests\test_workspace_core.py',
'policy_packs\government_strict_v1\policy.json',
'policy_packs\developer_controlled_v1\policy.json',
'policy_packs\client_isolated_v1\policy.json',
'policy_packs\research_read_prepare_v1\policy.json',
'scripts\Install-MultiWorkspaceCorePolicyPacksV1.ps1'
)
$missing=@($required | Where-Object { -not (Test-Path (Join-Path $PackageRoot $_) -PathType Leaf) })
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)";"MISSING_FILES=$($missing -join ';')"
if($missing.Count){throw 'CANDIDATE_REQUIRED_FILES_MISSING'}
$python=(Get-Command python -ErrorAction SilentlyContinue)
if($null -eq $python){$python=(Get-Command py -ErrorAction Stop)}
$pyFiles=Get-ChildItem (Join-Path $PackageRoot 'backend\src') -Filter '*.py' -Recurse | Select-Object -ExpandProperty FullName
& $python.Source -m py_compile @pyFiles
if($LASTEXITCODE -ne 0){throw 'PYTHON_COMPILE_FAILED'}
$node=Get-Command node -ErrorAction Stop
& $node.Source --check (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\workspace_core\static\app.js')
if($LASTEXITCODE -ne 0){throw 'NODE_CHECK_FAILED'}
$all=Get-Content (Join-Path $PackageRoot 'backend\src\palwakf_local_agents\workspace_core\store.py') -Raw -Encoding UTF8
$markers=@('NO_CROSS_WORKSPACE_READ_WRITE_TOOL_MEMORY_OR_AUDIT_ACCESS','NOT_MIGRATED_LEGACY_STATE_REMAINS_SEPARATE','WORKSPACE_STORAGE_AND_OPERATIONS_BINDING_REQUIRES_SEPARATE_APPROVAL')
$fails=@($markers | Where-Object {$all -notmatch [regex]::Escape($_)})
"CONTRACT_MARKER_FAILURE_COUNT=$($fails.Count)";"CONTRACT_MARKER_FAILURES=$($fails -join ';')"
if($fails.Count){throw 'CONTRACT_MARKERS_MISSING'}
"CANDIDATE_SCOPE=MULTI_WORKSPACE_CORE_POLICY_PACKS_OBSERVABILITY_ONLY"
"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED";"SYNTAX_GATE_RESULT=PASS"
