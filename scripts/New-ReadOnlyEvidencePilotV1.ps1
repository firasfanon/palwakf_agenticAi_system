[CmdletBinding()]
param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference='Stop'
$Root=[System.IO.Path]::GetFullPath($ProjectRoot)
$template=Join-Path $Root 'tasks/templates/PILOT_READ_ONLY_CONTEXT_EVIDENCE_TASK_V1.json'
$outDir=Join-Path $Root 'tasks/inbox'
$outPath=Join-Path $outDir 'PILOT_READ_ONLY_CONTEXT_EVIDENCE_001.json'
if (-not (Test-Path -LiteralPath $template)) { throw "PILOT_TEMPLATE_NOT_FOUND=$template" }
if (Test-Path -LiteralPath $outPath) { throw "PILOT_TASK_ALREADY_EXISTS=$outPath" }
$reference=Join-Path $Root 'reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md'
if (-not (Test-Path -LiteralPath $reference -PathType Leaf)) { throw "PILOT_REFERENCE_NOT_FOUND=$reference" }
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Copy-Item -LiteralPath $template -Destination $outPath -Force
"PILOT_TASK_CREATED=$outPath"
'PILOT_RISK=LOW'
'PILOT_AUTONOMY=L0_READ_ONLY'
'PILOT_REFERENCE_CLASSIFICATION=NON_SENSITIVE_APPROVED_REFERENCE'
'HUMAN_APPROVAL_REQUIRED=YES'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
