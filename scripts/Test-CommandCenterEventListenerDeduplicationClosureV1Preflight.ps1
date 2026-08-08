
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot,
  [Parameter(Mandatory = $true)][string]$PackageRoot
)
$ErrorActionPreference = "Stop"
$expectedPreimage = "FD3A453DE80F034521A30A7AAF2E8F4087D33DBF80756BC6BA9D7576EE98803D"
$expectedPostimage = "D83F8709428C047D9229ACD9C232BF1F552A078BBBA42B141D7FF7566006CD1E"
$target = Join-Path $ProjectRoot "backend\src\palwakf_local_agents\command_center\static\app.js"
$candidate = Join-Path $PackageRoot "backend\src\palwakf_local_agents\command_center\static\app.js"
if(-not (Test-Path -LiteralPath $target -PathType Leaf)){throw "TARGET_APP_JS_NOT_FOUND=$target"}
if(-not (Test-Path -LiteralPath $candidate -PathType Leaf)){throw "CANDIDATE_APP_JS_NOT_FOUND=$candidate"}
$targetHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
$candidateHash=(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
"TARGET_PREIMAGE_SHA256=$targetHash"
"CANDIDATE_POSTIMAGE_SHA256=$candidateHash"
"KNOWN_PREIMAGE_SHA256=$expectedPreimage"
"EXPECTED_POSTIMAGE_SHA256=$expectedPostimage"
if($targetHash -ne $expectedPreimage){throw "UNEXPECTED_PREIMAGE_SHA256=$targetHash"}
if($candidateHash -ne $expectedPostimage){throw "CANDIDATE_POSTIMAGE_HASH_UNEXPECTED=$candidateHash"}
$node=Get-Command node -ErrorAction Stop
& $node.Source --check $target
if($LASTEXITCODE -ne 0){throw "TARGET_APP_JS_NODE_CHECK_FAILED"}
$text=Get-Content -LiteralPath $target -Raw -Encoding UTF8
if($text -notmatch [regex]::Escape('function wire()')){throw "EXPECTED_RECURSIVE_WIRE_PREIMAGE_NOT_FOUND"}
if($text -notmatch [regex]::Escape('wire()}catch')){throw "EXPECTED_RENDER_WIRE_CALL_PREIMAGE_NOT_FOUND"}
"PREIMAGE_EVENT_WIRING=RECURSIVE_PER_RENDER"
"TARGET_MUTATION_SCOPE=ONE_STATIC_FILE_ONLY"
"APP_ENTRYPOINT_MUTATION=NONE"
"ROUTER_MUTATION=NONE"
"STORE_MUTATION=NONE"
"SQLITE_WRITE=NONE"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PREFLIGHT_RESULT=PASS"
