[CmdletBinding(SupportsShouldProcess)]
param([Parameter(Mandatory=$true)][string]$ProjectRoot,[Parameter(Mandatory=$true)][string]$BackupRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$BackupRoot = (Resolve-Path -LiteralPath $BackupRoot).Path
$manifestPath = Join-Path $BackupRoot 'apply_preimage_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'ROLLBACK_MANIFEST_NOT_FOUND' }
$items = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
foreach ($item in $items) {
  $rel = [string]$item.relative_path
  $target = Join-Path $ProjectRoot ($rel -replace '/', '\\')
  $backup = Join-Path $BackupRoot ($rel -replace '/', '\\')
  if ([bool]$item.existed_before) {
    if ($PSCmdlet.ShouldProcess($target, 'Restore preimage')) { New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null; Copy-Item -LiteralPath $backup -Destination $target -Force }
  } elseif (Test-Path -LiteralPath $target) {
    if ($PSCmdlet.ShouldProcess($target, 'Remove candidate-created file')) { Remove-Item -LiteralPath $target -Force }
  }
}
'ROLLBACK=PASS'
