[CmdletBinding()]
param([string]$ProjectRoot = "")
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = (Split-Path -Parent $PSScriptRoot) }
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$manifestPath = Join-Path $PSScriptRoot 'legacy_write_authorization_closure_v1_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'LEGACY_WRITE_AUTH_MANIFEST_NOT_FOUND' }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$entries = @($manifest.files)
$mismatches = @()
foreach ($entry in $entries) {
  $rel = [string]$entry.relative_path
  $target = Join-Path $ProjectRoot ($rel -replace '/', '\\')
  if (-not (Test-Path -LiteralPath $target)) { $mismatches += $rel; continue }
  $got = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToUpperInvariant()
  if ($got -ne [string]$entry.postimage_sha256) { $mismatches += $rel }
}
$tokens = $null; $parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile($PSCommandPath, [ref]$tokens, [ref]$parseErrors) | Out-Null
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$pythonFiles = @($entries | Where-Object { ([string]$_.relative_path).EndsWith('.py') } | ForEach-Object { Join-Path $ProjectRoot (([string]$_.relative_path) -replace '/', '\\') })
$compileCode = 'import pathlib,sys; [compile(pathlib.Path(p).read_text(encoding="utf-8"), p, "exec") for p in sys.argv[1:]]'
& $python -c $compileCode @pythonFiles
$pythonExit = $LASTEXITCODE
$appPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\app.py'
$goPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_operations\router.py'
$lacPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\local_agent_core\router.py'
$gcfPath = Join-Path $ProjectRoot 'backend\src\palwakf_local_agents\governed_capability_foundation\router.py'
$clientPath = Join-Path $ProjectRoot 'frontend\src\lib\client.ts'
$postCount = @((Select-String -LiteralPath $appPath -Pattern '@app\.post' -AllMatches).Matches).Count + @((Select-String -LiteralPath $goPath -Pattern '@api\.post' -AllMatches).Matches).Count + @((Select-String -LiteralPath $lacPath -Pattern '@api\.post' -AllMatches).Matches).Count + @((Select-String -LiteralPath $gcfPath -Pattern '@api\.post' -AllMatches).Matches).Count
$checks = [ordered]@{
  postimage_hashes_match = ($mismatches.Count -eq 0)
  post_route_count_is_15 = ($postCount -eq 15)
  unscoped_legacy_task_disabled = (Select-String -LiteralPath $appPath -Pattern 'LEGACY_UNSCOPED_WRITE_ROUTE_DISABLED' -Quiet)
  governed_operations_requires_authenticated_actor = (Select-String -LiteralPath $goPath -Pattern 'Depends\(authenticated_actor\)' -Quiet)
  local_agent_core_requires_authenticated_actor = (Select-String -LiteralPath $lacPath -Pattern 'Depends\(authenticated_actor\)' -Quiet)
  commercial_legacy_write_denied = (Select-String -LiteralPath $goPath -Pattern 'commercial_persistence_supported=False' -Quiet)
  react_write_remains_disabled = -not (Select-String -LiteralPath $clientPath -Pattern 'POST|PUT|PATCH|DELETE' -Quiet)
}
$pass = ($parseErrors.Count -eq 0) -and ($pythonExit -eq 0) -and (-not ($checks.Values -contains $false))
"PROJECT_ROOT=$ProjectRoot"
"EXPECTED_POSTIMAGE_COUNT=$($entries.Count)"
"POSTIMAGE_MISMATCH_COUNT=$($mismatches.Count)"
"POWERSHELL_PARSE_ERROR_COUNT=$($parseErrors.Count)"
"PYTHON_STATIC_COMPILE_EXIT=$pythonExit"
"POST_ROUTE_COUNT=$postCount"
$checks.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
if ($mismatches.Count -gt 0) { "POSTIMAGE_MISMATCHES=$($mismatches -join ';')" }
"FINAL_RESULT=$(if ($pass) { 'PASS' } else { 'FAIL' })"
if (-not $pass) { exit 1 }
