[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateNotNullOrEmpty()]
  [string]$BackupRoot
)

$ErrorActionPreference = 'Stop'
$BackupRoot = [System.IO.Path]::GetFullPath($BackupRoot)
$manifestPath = Join-Path $BackupRoot 'rollback_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "ROLLBACK_MANIFEST_NOT_FOUND: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$projectRoot = $manifest.project_root
if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) { throw "PROJECT_ROOT_NOT_FOUND: $projectRoot" }

foreach ($relative in @($manifest.restored_files)) {
  $source = Join-Path $BackupRoot $relative
  $target = Join-Path $projectRoot $relative
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
  Copy-Item -LiteralPath $source -Destination $target -Force
}
foreach ($relative in @($manifest.new_files)) {
  $target = Join-Path $projectRoot $relative
  if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target -Force }
}

Write-Output "PROJECT_ROOT=$projectRoot"
Write-Output "BACKUP_ROOT=$BackupRoot"
Write-Output 'ROLLBACK_RESULT=PASS'
