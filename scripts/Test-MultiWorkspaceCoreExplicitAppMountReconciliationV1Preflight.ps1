[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$PackageRoot
)
$ErrorActionPreference='Stop'
$app=Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$contractPath=Join-Path $PackageRoot 'contracts\workspace_core_source_contract.json'
if(-not(Test-Path $app -PathType Leaf)){throw "APP_PY_NOT_FOUND=$app"}
if(-not(Test-Path $contractPath -PathType Leaf)){throw "SOURCE_CONTRACT_NOT_FOUND=$contractPath"}
$contract=Get-Content $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json

# PowerShell 5.1 note: materialize the PSCustomObject note-properties explicitly.
# Accessing .Count directly on PSObject.Properties can enumerate child member counts
# and produce a non-scalar sequence such as "1 1 ...". This contract must use one scalar count.
$sourceProperties=@(
  $contract.source_files.PSObject.Properties |
  Where-Object { $_.MemberType -eq 'NoteProperty' }
)
$expectedCount=[int]$sourceProperties.Count
$fail=@()
$exact=0
foreach($property in $sourceProperties){
  $relative=[string]$property.Name
  $expected=[string]$property.Value
  $target=Join-Path $ProjectRoot $relative
  if(-not(Test-Path $target -PathType Leaf)){
    $fail+="WORKSPACE_CORE_SOURCE_MISSING=$relative"
    continue
  }
  $actual=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if($actual -ne $expected){
    $fail+="WORKSPACE_CORE_SOURCE_HASH_MISMATCH=$relative"
  } else {
    $exact++
  }
}
$appText=Get-Content $app -Raw -Encoding UTF8
$goImport='from .governed_operations import mount_governed_operations'
$goMount='mount_governed_operations(app, project_root=PROJECT_ROOT)'
$wsImport='from .workspace_core import mount_workspace_core'
$wsMount='mount_workspace_core(app, project_root=PROJECT_ROOT)'
$goImportCount=([regex]::Matches($appText,[regex]::Escape($goImport))).Count
$goMountCount=([regex]::Matches($appText,[regex]::Escape($goMount))).Count
$wsImportCount=([regex]::Matches($appText,[regex]::Escape($wsImport))).Count
$wsMountCount=([regex]::Matches($appText,[regex]::Escape($wsMount))).Count
if($goImportCount -ne 1){$fail+="GOVERNED_OPERATIONS_IMPORT_ANCHOR_COUNT=$goImportCount"}
if($goMountCount -ne 1){$fail+="GOVERNED_OPERATIONS_MOUNT_ANCHOR_COUNT=$goMountCount"}
if($wsImportCount -ne 0){$fail+="WORKSPACE_CORE_IMPORT_MUST_BE_ABSENT_COUNT=$wsImportCount"}
if($wsMountCount -ne 0){$fail+="WORKSPACE_CORE_MOUNT_MUST_BE_ABSENT_COUNT=$wsMountCount"}
$sourceHashesPass=($expectedCount -gt 0 -and $exact -eq $expectedCount)
"WORKSPACE_CORE_SOURCE_EXPECTED_COUNT=$expectedCount"
"WORKSPACE_CORE_SOURCE_EXACT_MATCH_COUNT=$exact"
"PRECONDITION_WORKSPACE_CORE_SOURCE_HASHES=$(if($sourceHashesPass){'PASS'}else{'FAIL'})"
"GOVERNED_OPERATIONS_IMPORT_ANCHOR_COUNT=$goImportCount"
"GOVERNED_OPERATIONS_MOUNT_ANCHOR_COUNT=$goMountCount"
"WORKSPACE_CORE_IMPORT_ABSENT=$(if($wsImportCount -eq 0){'PASS'}else{'FAIL'})"
"WORKSPACE_CORE_MOUNT_ABSENT=$(if($wsMountCount -eq 0){'PASS'}else{'FAIL'})"
"APP_PY_SHA256=$((Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash)"
"PREFLIGHT_FAILURE_COUNT=$($fail.Count)"
"PREFLIGHT_FAILURES=$($fail -join ';')"
"PREFLIGHT_REPORTING_CONSISTENCY=$(if($sourceHashesPass -and $expectedCount -eq 17){'PASS'}else{'FAIL'})"
"TARGET_MUTATION_SCOPE=APP_PY_ONLY"
"WORKSPACE_CORE_SOURCE_MUTATION=NONE"
"POLICY_PACKS_MUTATION=NONE"
"COMMAND_CENTER_MUTATION=NONE"
"GOVERNED_OPERATIONS_MUTATION=NONE"
"LOCAL_SQLITE_WRITE=NONE_DURING_INSTALL"
"LEGACY_MIGRATION=NONE"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
if($fail.Count){throw 'PREFLIGHT_FAILED'}
if(-not $sourceHashesPass){throw 'PREFLIGHT_SOURCE_HASH_CONTRACT_FAILED'}
"PREFLIGHT_RESULT=PASS"
