[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)] [ValidateSet('Inventory','ReadText','SearchText','Hash')] [string]$Operation,
  [Parameter(Mandatory = $true)] [string]$RelativePath,
  [string]$SearchText = '',
  [int]$MaxResults = 50,
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$allowedRoots = @('reference_sources/approved','governance','task_contracts','memory/approved')
$normalized = $RelativePath.Replace('/','\\').TrimStart('\\')
if ([System.IO.Path]::IsPathRooted($normalized) -or $normalized -match '(^|\\)\.\.(\\|$)') { throw 'TOOL_GATEWAY_PATH_DENIED' }
$allowed = $false
foreach ($prefix in $allowedRoots) {
  $p = $prefix.Replace('/','\\')
  if ($normalized -eq $p -or $normalized.StartsWith("$p\\", [System.StringComparison]::OrdinalIgnoreCase)) { $allowed = $true; break }
}
if (-not $allowed) { throw "TOOL_GATEWAY_ROOT_DENIED=$RelativePath" }
$target = Join-Path $Root $normalized
if (-not (Test-Path -LiteralPath $target)) { throw "TOOL_GATEWAY_TARGET_NOT_FOUND=$target" }

switch ($Operation) {
  'Inventory' {
    Get-ChildItem -LiteralPath $target -Recurse -File | Select-Object -First $MaxResults | ForEach-Object { $_.FullName.Substring($Root.Length).TrimStart('\\') }
  }
  'ReadText' {
    if ((Get-Item -LiteralPath $target).PSIsContainer) { throw 'READTEXT_REQUIRES_FILE' }
    Get-Content -LiteralPath $target -Raw -Encoding UTF8
  }
  'SearchText' {
    if ([string]::IsNullOrWhiteSpace($SearchText)) { throw 'SEARCHTEXT_REQUIRED' }
    Get-ChildItem -LiteralPath $target -Recurse -File | Select-Object -First 500 | Select-String -SimpleMatch -Pattern $SearchText | Select-Object -First $MaxResults | ForEach-Object { "$($_.Path.Substring($Root.Length).TrimStart('\\')):$($_.LineNumber):$($_.Line)" }
  }
  'Hash' {
    if ((Get-Item -LiteralPath $target).PSIsContainer) { throw 'HASH_REQUIRES_FILE' }
    (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  }
}
'TOOL_MODE=READ_ONLY'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
