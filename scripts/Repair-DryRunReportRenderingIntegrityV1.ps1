[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$runnerPath = Join-Path $Root 'scripts\Invoke-ReadOnlyContextEvidenceRunnerV1.ps1'

if (-not (Test-Path -LiteralPath $runnerPath)) {
  throw "RUNNER_NOT_FOUND=$runnerPath"
}

$content = Get-Content -LiteralPath $runnerPath -Raw -Encoding UTF8
$content = $content.Replace("`r`n", "`n")

$oldFlagsLine = '$flags = @($_.security_flags)'
$newFlagsLine = '$flags = @($_.security_flags | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })'

if (-not $content.Contains($oldFlagsLine)) {
  throw 'EXPECTED_SECURITY_FLAGS_LINE_NOT_FOUND'
}

if ($content.Contains($newFlagsLine)) {
  throw 'SECURITY_FLAGS_FILTER_ALREADY_PRESENT'
}

$oldReportStart = '$report = @"'
$newReportStart = @'
$codeFence = '```'

$report = @"
'@
$newReportStart = $newReportStart.Replace("`r`n", "`n")

if (-not $content.Contains($oldReportStart)) {
  throw 'EXPECTED_REPORT_START_NOT_FOUND'
}

$oldReportBlock = @'
## Deterministic model-output validation
```text
$($validationLines -join "`n")
```

## Raw model output
```text
$rawOutput
```
'@
$oldReportBlock = $oldReportBlock.Replace("`r`n", "`n")

$newReportBlock = @'
## Deterministic model-output validation
${codeFence}text
$($validationLines -join "`n")
${codeFence}

## Raw model output
${codeFence}text
$rawOutput
${codeFence}
'@
$newReportBlock = $newReportBlock.Replace("`r`n", "`n")

if (-not $content.Contains($oldReportBlock)) {
  throw 'EXPECTED_REPORT_FENCE_BLOCK_NOT_FOUND'
}

$updated = $content.Replace($oldFlagsLine, $newFlagsLine)
$updated = $updated.Replace($oldReportStart, $newReportStart)
$updated = $updated.Replace($oldReportBlock, $newReportBlock)

if ($updated.Contains($oldFlagsLine)) {
  throw 'SECURITY_FLAGS_LINE_REPLACEMENT_FAILED'
}

if ($updated.Contains('```text')) {
  throw 'RAW_MARKDOWN_FENCE_REMAINS'
}

if (-not $updated.Contains('${codeFence}text')) {
  throw 'CODE_FENCE_VARIABLE_REPLACEMENT_FAILED'
}

if ($PSCmdlet.ShouldProcess($runnerPath, 'Apply dry-run report rendering integrity repair')) {
  Set-Content -LiteralPath $runnerPath -Value $updated -Encoding UTF8
}

"REPAIR_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"RUNNER_PATH=$runnerPath"
'SECURITY_EMPTY_FLAGS_FILTER=APPLIED'
'MARKDOWN_FENCE_RENDERING=VARIABLE_BASED'
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
