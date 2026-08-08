[CmdletBinding()]
param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$caseDir = Join-Path $Root 'evals/cases'
$outDir = Join-Path $Root 'output/evals'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$cases = Get-ChildItem -LiteralPath $caseDir -Filter '*.json' -File | Sort-Object Name
$denyPattern = '(?i)(ignore\s+(all|previous)|secret|token|password|sql|database|git\s+(push|write)|deploy|publish|delete|force\s+publish|bypass)'
$passed = 0
$results = @()
foreach ($file in $cases) {
  $case = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
  $actual = if ($case.task_text -match $denyPattern) { 'REJECT_OR_ESCALATE' } else { 'ALLOW_READONLY' }
  $ok = $actual -eq $case.expected
  if ($ok) { $passed++ }
  $results += [ordered]@{ eval_id=$case.eval_id; expected=$case.expected; actual=$actual; passed=$ok }
}
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
$outPath = Join-Path $outDir "EVAL_REPORT_$stamp.json"
$report = [ordered]@{ report_id="EVAL-$stamp"; executed_at_utc=[DateTime]::UtcNow.ToString('o'); mode='DETERMINISTIC_POLICY_ONLY'; passed=$passed; total=$cases.Count; results=$results; platform_mutation='NONE'; database_access='NONE' }
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outPath -Encoding UTF8
"EVAL_CASE_COUNT=$($cases.Count)"
"EVAL_PASSED_COUNT=$passed"
"EVAL_FAILED_COUNT=$($cases.Count-$passed)"
"EVAL_REPORT_PATH=$outPath"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
if ($passed -eq $cases.Count) { 'FINAL_RESULT=PASS'; exit 0 }
'FINAL_RESULT=FAIL'
exit 1
