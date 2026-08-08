[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot,

  [Parameter(Mandatory = $false)]
  [string]$OutputRoot = "",

  [Parameter(Mandatory = $false)]
  [string]$ReferenceDocsRoot = ""
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
  throw "PROJECT_ROOT_NOT_FOUND=$ProjectRoot"
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
  $parent = Split-Path -Parent $ProjectRoot
  $OutputRoot = Join-Path $parent 'baseline_snapshots'
}

$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$snapshotName = "PALWAKF_LOCAL_AGENTS_COMPREHENSIVE_SNAPSHOT_$stamp"
$stagingRoot = Join-Path $OutputRoot $snapshotName
$projectSnapshotRoot = Join-Path $stagingRoot 'project'
$zipPath = Join-Path $OutputRoot "$snapshotName.zip"

if (Test-Path -LiteralPath $stagingRoot) {
  Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}

if (Test-Path -LiteralPath $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $projectSnapshotRoot -Force | Out-Null

$excludedDirectoryNames = @(
  '.git',
  '.hg',
  '.svn',
  'node_modules',
  '.venv',
  'venv',
  '__pycache__',
  '.dart_tool',
  'build',
  'dist',
  '.gradle',
  '.cache',
  'cache',
  'tmp',
  'temp'
)

$excludedFileNames = @(
  '.env'
)

$excludedFilePatterns = @(
  '.env.*',
  '*.pem',
  '*.key',
  '*.pfx',
  '*.p12',
  '*credentials*.json',
  '*credential*.json',
  '*secret*.json',
  '*secrets*.json',
  '*token*.json'
)

$allDirectories = @(
  Get-ChildItem -LiteralPath $ProjectRoot -Force -Recurse -Directory |
    Sort-Object FullName
)

$includedDirectories = New-Object System.Collections.Generic.List[string]
$excludedDirectories = New-Object System.Collections.Generic.List[string]

foreach ($directory in $allDirectories) {
  $relative = $directory.FullName.Substring($ProjectRoot.Length).TrimStart('\', '/')
  $segments = @($relative -split '[\\/]')

  $isExcluded = $false

  foreach ($segment in $segments) {
    if ($excludedDirectoryNames -contains $segment) {
      $isExcluded = $true
      break
    }
  }

  if ($isExcluded) {
    [void]$excludedDirectories.Add($relative)
    continue
  }

  [void]$includedDirectories.Add($relative)
  $destinationDirectory = Join-Path $projectSnapshotRoot $relative
  New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
}

$allFiles = @(
  Get-ChildItem -LiteralPath $ProjectRoot -Force -Recurse -File |
    Sort-Object FullName
)

$copiedFiles = New-Object System.Collections.Generic.List[object]
$excludedFiles = New-Object System.Collections.Generic.List[object]

foreach ($file in $allFiles) {
  $relative = $file.FullName.Substring($ProjectRoot.Length).TrimStart('\', '/')
  $segments = @($relative -split '[\\/]')

  $directoryExcluded = $false

  foreach ($segment in $segments) {
    if ($excludedDirectoryNames -contains $segment) {
      $directoryExcluded = $true
      break
    }
  }

  if ($directoryExcluded) {
    [void]$excludedFiles.Add([PSCustomObject]@{
      path = $relative
      reason = 'EXCLUDED_DIRECTORY'
    })
    continue
  }

  $fileNameExcluded = $excludedFileNames -contains $file.Name

  if (-not $fileNameExcluded) {
    foreach ($pattern in $excludedFilePatterns) {
      if ($file.Name -like $pattern) {
        $fileNameExcluded = $true
        break
      }
    }
  }

  if ($fileNameExcluded) {
    [void]$excludedFiles.Add([PSCustomObject]@{
      path = $relative
      reason = 'SENSITIVE_OR_SECRET_CANDIDATE'
    })
    continue
  }

  $destination = Join-Path $projectSnapshotRoot $relative
  $destinationDirectory = Split-Path -Parent $destination
  New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
  Copy-Item -LiteralPath $file.FullName -Destination $destination -Force

  [void]$copiedFiles.Add([PSCustomObject]@{
    path = $relative
    bytes = $file.Length
    sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
  })
}

$treePath = Join-Path $stagingRoot 'PROJECT_DIRECTORY_TREE.txt'
$treeLines = New-Object System.Collections.Generic.List[string]
[void]$treeLines.Add("PROJECT_ROOT=$ProjectRoot")
[void]$treeLines.Add("SNAPSHOT_SCOPE=SOURCE_AND_GOVERNANCE_ARTIFACTS_WITH_SENSITIVE_AND_VOLATILE_EXCLUSIONS")
[void]$treeLines.Add("")
[void]$treeLines.Add("[DIRECTORIES]")

foreach ($relative in $includedDirectories) {
  [void]$treeLines.Add($relative)
}

[void]$treeLines.Add("")
[void]$treeLines.Add("[EXCLUDED_DIRECTORIES]")

foreach ($relative in $excludedDirectories) {
  [void]$treeLines.Add($relative)
}

$treeLines | Set-Content -LiteralPath $treePath -Encoding UTF8

$manifestPath = Join-Path $stagingRoot 'SNAPSHOT_MANIFEST.json'
$manifest = [PSCustomObject]@{
  snapshot_id = $snapshotName
  generated_at_local = (Get-Date).ToString('o')
  project_root = $ProjectRoot
  scope = 'LOCAL_AGENTS_PROJECT_SOURCE_AND_GOVERNANCE_ARTIFACTS'
  exclusions = [PSCustomObject]@{
    directory_names = $excludedDirectoryNames
    file_names = $excludedFileNames
    file_patterns = $excludedFilePatterns
  }
  included_directory_count = $includedDirectories.Count
  excluded_directory_count = $excludedDirectories.Count
  copied_file_count = $copiedFiles.Count
  excluded_file_count = $excludedFiles.Count
  copied_files = @($copiedFiles)
  excluded_files = @($excludedFiles)
  execution_boundaries = [PSCustomObject]@{
    platform_mutation = 'NONE'
    database_access = 'NONE'
    git_write = 'NONE'
    deployment = 'NONE'
    secrets_included = 'NO'
    project_source_mutation = 'NONE'
  }
}

$manifest |
  ConvertTo-Json -Depth 20 |
  Set-Content -LiteralPath $manifestPath -Encoding UTF8

if (-not [string]::IsNullOrWhiteSpace($ReferenceDocsRoot)) {
  $ReferenceDocsRoot = [System.IO.Path]::GetFullPath($ReferenceDocsRoot)

  if (-not (Test-Path -LiteralPath $ReferenceDocsRoot)) {
    throw "REFERENCE_DOCS_ROOT_NOT_FOUND=$ReferenceDocsRoot"
  }

  $referenceDestination = Join-Path $stagingRoot 'baseline_documents'
  New-Item -ItemType Directory -Path $referenceDestination -Force | Out-Null

  Get-ChildItem -LiteralPath $ReferenceDocsRoot -File |
    Where-Object {
      $_.Extension -in @('.md', '.txt', '.json')
    } |
    ForEach-Object {
      Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $referenceDestination $_.Name) -Force
    }
}

Compress-Archive `
  -LiteralPath $stagingRoot `
  -DestinationPath $zipPath `
  -Force

$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash

"SNAPSHOT_STATUS=COMPLETE"
"SNAPSHOT_ROOT=$stagingRoot"
"SNAPSHOT_ZIP=$zipPath"
"SNAPSHOT_ZIP_SHA256=$zipHash"
"COPIED_FILE_COUNT=$($copiedFiles.Count)"
"EXCLUDED_FILE_COUNT=$($excludedFiles.Count)"
"INCLUDED_DIRECTORY_COUNT=$($includedDirectories.Count)"
"EXCLUDED_DIRECTORY_COUNT=$($excludedDirectories.Count)"
'PROJECT_SOURCE_MUTATION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_INCLUDED=NO'
