[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$SourceProjectRoot,
  [Parameter(Mandatory = $true)][string]$CandidateRoot,
  [Parameter(Mandatory = $true)][string]$WorktreePath,
  [Parameter(Mandatory = $true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
function Get-Sha256([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant() }
function Require([bool]$Condition, [string]$Code) { if (-not $Condition) { throw $Code } }
$SourceProjectRoot = (Resolve-Path -LiteralPath $SourceProjectRoot).Path
$CandidateRoot = (Resolve-Path -LiteralPath $CandidateRoot).Path
$PayloadRoot = Join-Path $CandidateRoot 'PATCH_PAYLOAD'
$Preimage = Get-Content (Join-Path $CandidateRoot 'PREIMAGE_SHA256.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Postimage = Get-Content (Join-Path $CandidateRoot 'POSTIMAGE_SHA256.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Require (Test-Path (Join-Path $SourceProjectRoot '.git')) 'SOURCE_GIT_ROOT_REQUIRED'
Require (-not (Test-Path -LiteralPath $WorktreePath)) 'WORKTREE_PATH_MUST_BE_ABSENT'
$dirty = git -C $SourceProjectRoot status --porcelain
$dirtyText = [string]($dirty -join "`n")
Require ([string]::IsNullOrWhiteSpace($dirtyText)) 'SOURCE_PROJECT_MUST_BE_CLEAN'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
# No source mutation: create an independent detached worktree.
git -C $SourceProjectRoot worktree add --detach $WorktreePath HEAD
try {
  $WorktreePath = (Resolve-Path -LiteralPath $WorktreePath).Path
  foreach ($prop in $Preimage.PSObject.Properties) {
    $target = Join-Path $WorktreePath $prop.Name
    if ($prop.Value -eq '__ABSENT__') { Require (-not (Test-Path -LiteralPath $target)) "PREIMAGE_EXPECTED_ABSENT=$($prop.Name)"; continue }
    Require (Test-Path -LiteralPath $target) "PREIMAGE_MISSING=$($prop.Name)"
    Require ((Get-Sha256 $target) -eq $prop.Value) "PREIMAGE_HASH_MISMATCH=$($prop.Name)"
  }
  Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($PayloadRoot.Length).TrimStart([char[]]@([char]'\',[char]'/'))
    $destination = Join-Path $WorktreePath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
  }
  foreach ($prop in $Postimage.PSObject.Properties) {
    $target = Join-Path $WorktreePath $prop.Name
    Require (Test-Path -LiteralPath $target) "POSTIMAGE_MISSING=$($prop.Name)"
    Require ((Get-Sha256 $target) -eq $prop.Value) "POSTIMAGE_HASH_MISMATCH=$($prop.Name)"
  }
  $staticGate = Join-Path $CandidateRoot 'scripts/Test-ProductConsoleReadOnlyCandidateStaticGate.ps1'
  & $staticGate -ProjectRoot $WorktreePath -OutputDirectory (Join-Path $OutputDirectory 'STATIC_GATE')
  Push-Location (Join-Path $WorktreePath 'frontend')
  try {
    npm ci --ignore-scripts --offline
    npm run check
    npm run build
  } finally { Pop-Location }
  $report = [ordered]@{
    authorization = 'AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_APPLY_V1_ISOLATED_WORKTREE_ONLY'
    execution_scope = 'ISOLATED_WORKTREE_ONLY'
    source_project_mutation = 'NONE'
    preimage = 'PASS'; postimage = 'PASS'; static_gate = 'PASS'; npm_ci_offline = 'PASS'; tsc = 'PASS'; vite_build = 'PASS'
    runtime_uat = 'NOT_EXECUTED'; sqlite_migration = 'NOT_EXECUTED'; model_execution = 'NOT_EXECUTED'; pilot_execution = 'NOT_EXECUTED'; production = 'NOT_APPROVED'
  }
  $report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutputDirectory 'APPLY_REPORT.json') -Encoding UTF8
  $report.GetEnumerator() | ForEach-Object { '{0}={1}' -f $_.Key.ToUpperInvariant(), $_.Value }
} catch {
  # Preserve the isolated worktree for forensic review; never touch the source project.
  throw
}
