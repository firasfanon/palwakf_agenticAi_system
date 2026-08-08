[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
'MANIFEST_MULTI_WORKSPACE_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_PREFLIGHT_REPORTING_FIX.md',
'APPLY_GUIDE_MULTI_WORKSPACE_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_PREFLIGHT_REPORTING_FIX_AR.md',
'VALIDATION_REPORT_MULTI_WORKSPACE_CORE_EXPLICIT_APP_MOUNT_RECONCILIATION_V1_PREFLIGHT_REPORTING_FIX.md',
'contracts\workspace_core_source_contract.json',
'scripts\Test-MultiWorkspaceCoreExplicitAppMountReconciliationV1Preflight.ps1',
'scripts\Install-MultiWorkspaceCoreExplicitAppMountReconciliationV1.ps1',
'scripts\Test-MultiWorkspaceCoreExplicitAppMountReconciliationV1PostApply.ps1'
)
$missing=@()
foreach($relative in $required){
  if(-not(Test-Path (Join-Path $PackageRoot $relative) -PathType Leaf)){$missing+=$relative}
}
$preflight=Get-Content (Join-Path $PackageRoot 'scripts\Test-MultiWorkspaceCoreExplicitAppMountReconciliationV1Preflight.ps1') -Raw -Encoding UTF8
$installer=Get-Content (Join-Path $PackageRoot 'scripts\Install-MultiWorkspaceCoreExplicitAppMountReconciliationV1.ps1') -Raw -Encoding UTF8
$preflightMarkers=@(
'$sourceProperties=@(',
'NoteProperty',
'$expectedCount=[int]$sourceProperties.Count',
'WORKSPACE_CORE_SOURCE_EXPECTED_COUNT=$expectedCount',
'PRECONDITION_WORKSPACE_CORE_SOURCE_HASHES=',
'PREFLIGHT_REPORTING_CONSISTENCY='
)
$installerMarkers=@(
'TARGET_MUTATION_SCOPE=APP_PY_ONLY',
'from .workspace_core import mount_workspace_core',
'mount_workspace_core(app, project_root=PROJECT_ROOT)',
'SupportsShouldProcess=$true',
'WORKSPACE_CORE_SOURCE_HASH_MISMATCH'
)
$bad=@()
foreach($marker in $preflightMarkers){if($preflight -notmatch [regex]::Escape($marker)){$bad+="PREFLIGHT_MARKER_MISSING=$marker"}}
foreach($marker in $installerMarkers){if($installer -notmatch [regex]::Escape($marker)){$bad+="INSTALLER_MARKER_MISSING=$marker"}}
"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$($missing -join ';')"
"CONTRACT_MARKER_FAILURE_COUNT=$($bad.Count)"
"CONTRACT_MARKER_FAILURES=$($bad -join ';')"
"CANDIDATE_ROLE=PREFLIGHT_REPORTING_FIX_ONLY_WITH_UNCHANGED_APP_MOUNT_INSTALLER"
"PROJECT_MUTATION=NONE_DURING_SYNTAX_GATE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
if($missing.Count -or $bad.Count){throw 'SYNTAX_GATE_FAILED'}
"SYNTAX_GATE_RESULT=PASS"
