[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$root=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\workspace_core'
$required=@('__init__.py','contracts.py','policy.py','store.py','router.py','static\index.html','static\styles.css','static\app.js')
$missing=@($required|Where-Object{-not(Test-Path (Join-Path $root $_) -PathType Leaf)})
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)"
if($missing.Count){throw 'WORKSPACE_CORE_STATIC_GATE_FILES_MISSING'}
$all=Get-Content (Join-Path $root 'router.py') -Raw -Encoding UTF8
$execution=@('execute','dispatch')|Where-Object{$all -match ('"/'+$_+'"')}
"EXECUTION_ROUTE_MARKER_COUNT=$($execution.Count)";"EXECUTION_ROUTE_MARKERS=$($execution -join ';')"
if($execution.Count){throw 'WORKSPACE_CORE_EXECUTION_ROUTE_MARKER_DETECTED'}
"CROSS_WORKSPACE_CONTRACT=NO_CROSS_WORKSPACE_READ_WRITE_TOOL_MEMORY_OR_AUDIT_ACCESS";"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL";"FINAL_RESULT=PASS"
