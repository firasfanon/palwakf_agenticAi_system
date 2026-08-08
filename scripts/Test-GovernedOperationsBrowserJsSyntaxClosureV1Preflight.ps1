[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$PackageRoot
)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
$package=(Resolve-Path -LiteralPath $PackageRoot).Path
$relative='backend\src\palwakf_local_agents\governed_operations\static\app.js'
$target=Join-Path $project $relative
$source=Join-Path $package $relative
$failures=@()
if(-not(Test-Path -LiteralPath $target -PathType Leaf)){$failures+="TARGET_APP_JS_MISSING=$target"}
if(-not(Test-Path -LiteralPath $source -PathType Leaf)){$failures+="PACKAGE_APP_JS_MISSING=$source"}
$targetHash=if(Test-Path -LiteralPath $target -PathType Leaf){(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash}else{''}
$sourceHash=if(Test-Path -LiteralPath $source -PathType Leaf){(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash}else{''}
$targetText=if(Test-Path -LiteralPath $target -PathType Leaf){Get-Content -LiteralPath $target -Raw -Encoding UTF8}else{''}
$malformed=[regex]::Matches($targetText,'\.split\("(\r?\n)"\)').Count
$fixed=[regex]::Matches($targetText,'\.split\("\\n"\)').Count
if($targetHash -ne '49B69C3936DE0DFC653FA2D0FD15BB848C17646B8F3DACA6B56E8249EFA9FD7A'){$failures+="UNEXPECTED_PREIMAGE_SHA256=$targetHash"}
if($sourceHash -ne '9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041'){$failures+="UNEXPECTED_CANDIDATE_SHA256=$sourceHash"}
if($malformed -ne 1){$failures+="PREIMAGE_MALFORMED_SPLIT_LITERAL_COUNT=$malformed"}
if($fixed -ne 0){$failures+="PREIMAGE_ALREADY_FIXED_SPLIT_LITERAL_COUNT=$fixed"}
Write-Output "PREFLIGHT_FAILURE_COUNT=$($failures.Count)"
Write-Output "PREFLIGHT_FAILURES=$($failures -join ';')"
Write-Output "EXPECTED_PREIMAGE_SHA256=49B69C3936DE0DFC653FA2D0FD15BB848C17646B8F3DACA6B56E8249EFA9FD7A"
Write-Output "OBSERVED_PREIMAGE_SHA256=$targetHash"
Write-Output "CANDIDATE_APP_JS_SHA256=$sourceHash"
Write-Output "PREIMAGE_MALFORMED_SPLIT_LITERAL_COUNT=$malformed"
Write-Output "PREIMAGE_FIXED_SPLIT_LITERAL_COUNT=$fixed"
Write-Output 'PATCH_SCOPE=ONE_STATIC_APP_JS_SYNTAX_CLOSURE_ONLY'
Write-Output 'APP_ENTRYPOINT_MUTATION=NONE'
Write-Output 'ROUTER_MUTATION=NONE'
Write-Output 'STORE_MUTATION=NONE'
Write-Output 'COMMAND_CENTER_MUTATION=NONE'
Write-Output 'LOCAL_SQLITE_WRITE=NONE'
Write-Output 'MODEL_EXECUTION=NONE'
Write-Output 'PILOT_EXECUTION=NOT_EXECUTED'
Write-Output 'PLATFORM_MUTATION=NONE'
Write-Output 'EXTERNAL_DATABASE_ACCESS=NONE'
if($failures.Count){Write-Output 'PREFLIGHT_RESULT=FAIL';exit 1}
Write-Output 'PREFLIGHT_RESULT=PASS'
