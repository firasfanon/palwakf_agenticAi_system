[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,
  [string]$OutputDirectory = (Join-Path $PWD "PRODUCT_CONSOLE_READ_ONLY_STATIC_GATE")
)
$ErrorActionPreference = "Stop"
$CandidateRoot = Split-Path -Parent $PSScriptRoot
$PayloadRoot = Join-Path $CandidateRoot "PATCH_PAYLOAD"
$PreimagePath = Join-Path $CandidateRoot "PREIMAGE_SHA256.json"
$PostimagePath = Join-Path $CandidateRoot "POSTIMAGE_SHA256.json"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Fail([string]$Code) { throw $Code }

$pre = Get-Content -LiteralPath $PreimagePath -Raw -Encoding UTF8 | ConvertFrom-Json
$post = Get-Content -LiteralPath $PostimagePath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in $pre.PSObject.Properties) {
  $target = Join-Path $ProjectRoot $property.Name
  if ($property.Value -eq "__ABSENT__") { if (Test-Path -LiteralPath $target) { Fail "PREIMAGE_EXPECTED_ABSENT=$($property.Name)" }; continue }
  if (-not (Test-Path -LiteralPath $target)) { Fail "PREIMAGE_MISSING=$($property.Name)" }
  if ((Get-Sha256 $target) -ne $property.Value) { Fail "PREIMAGE_HASH_MISMATCH=$($property.Name)" }
}

$forbidden = @('localStorage','sessionStorage','Authorization','Bearer','method:\s*["''](?:POST|PUT|PATCH|DELETE)["'']','dangerouslySetInnerHTML','model-pilot/drafts')
$payloadFiles = Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File -Filter '*.ts*'
foreach ($file in $payloadFiles) {
  $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
  foreach ($pattern in $forbidden) { if ($content -match $pattern) { Fail "FORBIDDEN_REACT_PATTERN=$pattern::$($file.Name)" } }
}
$client = Get-Content -LiteralPath (Join-Path $PayloadRoot 'frontend/src/api/client.ts') -Raw -Encoding UTF8
if ($client -notmatch 'method:\s*"GET"') { Fail 'GET_METHOD_NOT_DECLARED' }
if ($client -notmatch 'credentials:\s*"omit"') { Fail 'CREDENTIALS_OMIT_NOT_DECLARED' }

$report = [ordered]@{
  candidate_id = 'MEGA_BATCH_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_UX_UI_DISCOVERY_DESIGN_AND_GOVERNED_READ_ONLY_CANDIDATE_V1'
  source_project_mutation = 'NONE'
  preimage = 'PASS'
  read_only_lexical_gate = 'PASS'
  react_write_ui = 'ABSENT'
  runtime_uat = 'NOT_EXECUTED'
  result = 'STATIC_GATE_PASS'
}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'STATIC_GATE_REPORT.json') -Encoding UTF8
$report.GetEnumerator() | ForEach-Object { "{0}={1}" -f $_.Key.ToUpperInvariant(), $_.Value }
