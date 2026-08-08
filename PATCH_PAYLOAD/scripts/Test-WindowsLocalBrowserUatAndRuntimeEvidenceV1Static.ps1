# UTF-8 with BOM. Compatible with Windows PowerShell 5.1 and PowerShell 7+.
[CmdletBinding()]
param(
  [string]$ProjectRoot = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve after invocation context is available; compatible with Windows PowerShell 5.1.
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $scriptPathForRoot = $PSCommandPath
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { $scriptPathForRoot = $MyInvocation.MyCommand.Path }
  if ([string]::IsNullOrWhiteSpace($scriptPathForRoot)) { throw 'PROJECT_ROOT_REQUIRED__PASS_PROJECTROOT_OR_RUN_WITH_POWERSHELL_FILE_MODE.' }
  $scriptDirectoryForRoot = Split-Path -Parent $scriptPathForRoot
  $ProjectRoot = Split-Path -Parent $scriptDirectoryForRoot
}
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$required = @(
  'scripts/Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1',
  'scripts/Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1',
  'docs/UAT_REACT_WINDOWS_LOCAL_BROWSER_RUNTIME_EVIDENCE_V1_AR.md',
  'docs/WINDOWS_LOCAL_BROWSER_UAT_EVIDENCE_POLICY_V1_AR.md',
  'frontend/package.json',
  'frontend/package-lock.json',
  'frontend/src/api/client.ts',
  'frontend/vite.config.ts',
  'backend/src/palwakf_local_agents/app.py',
  'backend/src/palwakf_local_agents/settings.py'
)

$missing = @()
foreach ($relative in $required) {
  if (-not (Test-Path -LiteralPath (Join-Path $Root $relative))) { $missing += $relative }
}

$runnerPath = Join-Path $Root 'scripts/Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1'
$parserErrors = @()
if (Test-Path -LiteralPath $runnerPath) {
  $tokens = $null
  $parseErrors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($runnerPath, [ref]$tokens, [ref]$parseErrors)
  if ($null -ne $parseErrors) { $parserErrors = @($parseErrors) }
}

$client = if (Test-Path -LiteralPath (Join-Path $Root 'frontend/src/api/client.ts')) { Get-Content -LiteralPath (Join-Path $Root 'frontend/src/api/client.ts') -Raw -Encoding UTF8 } else { '' }
$app = if (Test-Path -LiteralPath (Join-Path $Root 'backend/src/palwakf_local_agents/app.py')) { Get-Content -LiteralPath (Join-Path $Root 'backend/src/palwakf_local_agents/app.py') -Raw -Encoding UTF8 } else { '' }
$settings = if (Test-Path -LiteralPath (Join-Path $Root 'backend/src/palwakf_local_agents/settings.py')) { Get-Content -LiteralPath (Join-Path $Root 'backend/src/palwakf_local_agents/settings.py') -Raw -Encoding UTF8 } else { '' }
$runner = if (Test-Path -LiteralPath $runnerPath) { Get-Content -LiteralPath $runnerPath -Raw -Encoding UTF8 } else { '' }
$packageLockPath = Join-Path $Root 'frontend/package-lock.json'
$packageLock = if (Test-Path -LiteralPath $packageLockPath) { Get-Content -LiteralPath $packageLockPath -Raw -Encoding UTF8 } else { '' }
$internalRegistryPrefix = 'https://packages.applied-caas-gateway1.internal.api.openai.org/artifactory/api/npm/npm-public/'
$internalRegistryResolvedCount = [regex]::Matches($packageLock, [regex]::Escape($internalRegistryPrefix)).Count
$publicRegistryResolvedCount = [regex]::Matches($packageLock, 'https://registry\.npmjs\.org/').Count

$checks = [ordered]@{
  runner_parser_error_count_zero = (@($parserErrors).Count -eq 0)
  runner_project_root_default_safe = (-not ($runner -match '\$ProjectRoot\s*=\s*\(Split-Path -Parent \$PSScriptRoot\)'))
  react_credentials_omit = ($client -match 'credentials:\s*"omit"')
  react_get_only_literal = ($client -match 'method:\s*"GET"')
  react_no_authorization_literal = (-not ($client -match '(?i)authorization|bearer'))
  react_no_web_storage_literal = (-not ($client -match '(?i)localStorage|sessionStorage'))
  app_loopback_default = ($settings -match "LOCAL_AGENT_HOST'.*127\.0\.0\.1")
  app_react_conditional_mount = ($app -match 'REACT_CONSOLE_INDEX\.is_file\(\)')
  runner_isolated_worktree = ($runner -match 'robocopy' -and $runner -match 'worktree')
  runner_forces_safe_flags = ($runner -match 'ALLOW_AGENT_EXECUTION' -and $runner -match 'ALLOW_PLATFORM_MUTATION' -and $runner -match 'ALLOW_DATABASE_ACCESS')
  runner_has_har_gate = ($runner -match 'browser_network\.har' -and $runner -match 'Resolve-HarEvidence' -and $runner -match 'HAR')
  runner_has_har_filename_reconciliation = ($runner -match 'function Resolve-HarEvidence' -and $runner -match 'RECONCILED_SINGLE_CANDIDATE' -and $runner -match 'browser_network_har_resolution\.json')
  runner_rejects_ambiguous_har_evidence = ($runner -match 'HAR_FILENAME_AMBIGUOUS' -and $runner -match 'MULTIPLE_HAR_FILES_REQUIRE_OPERATOR_SELECTION')
  runner_has_cleanup = ($runner -match 'Stop-IsolatedBrowserProfileProcesses' -and $runner -match 'Remove-IsolatedWorktreeWithRetries' -and $runner -match 'WORKTREE_CLEANUP')
  runner_scopes_browser_cleanup_to_isolated_profile = ($runner -match 'user-data-dir' -and $runner -match 'CommandLine' -and $runner -match 'profile_directory')
  runner_retries_worktree_cleanup = ($runner -match 'MaxAttempts = 5' -and $runner -match 'WORKTREE_CLEANUP_FAILED_AFTER_PROFILE_PROCESS_TERMINATION')
  runner_uses_npm_cmd = ($runner -match 'Resolve-NpmCmd' -and $runner -match 'npm\.cmd')
  runner_captures_process_stderr_by_exit_code = ($runner -match 'Invoke-DirectProcessLogged' -and $runner -match 'RedirectStandardError\s*=\s*\$true' -and $runner -match '\$process\.ExitCode' -and $runner -match 'EXTERNAL_COMMAND_FAILED')
  runner_headless_capture_avoids_stderr_pipeline = ($runner -notmatch '& \$Browser @arguments 2>&1' -and $runner -notmatch '& \$Browser @domArguments 2>&1')
  lockfile_no_internal_build_registry = ($internalRegistryResolvedCount -eq 0)
  lockfile_has_public_registry_resolved_urls = ($publicRegistryResolvedCount -gt 0)
  runner_registry_mode_forces_public_registry = ($runner -match 'https://registry\.npmjs\.org/')
  runner_registry_mode_uses_isolated_cache = ($runner -match 'npm-registry-cache' -and $runner -match "'--cache'")
}

"PROJECT_ROOT=$Root"
"REQUIRED_ITEM_COUNT=$($required.Count)"
"MISSING_ITEM_COUNT=$($missing.Count)"
"RUNNER_PARSER_ERROR_COUNT=$(@($parserErrors).Count)"
"LOCKFILE_INTERNAL_REGISTRY_RESOLVED_COUNT=$internalRegistryResolvedCount"
"LOCKFILE_PUBLIC_REGISTRY_RESOLVED_COUNT=$publicRegistryResolvedCount"
foreach ($key in $checks.Keys) { "$key=$($checks[$key])" }
if ($missing.Count -gt 0) {
  'MISSING_ITEMS='
  $missing | ForEach-Object { $_ }
}
if (@($parserErrors).Count -gt 0) {
  'RUNNER_PARSER_ERRORS='
  $parserErrors | ForEach-Object { "[$($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber)] $($_.Message)" }
}

$allPass = ($missing.Count -eq 0) -and -not ($checks.Values -contains $false)
if ($allPass) { 'FINAL_RESULT=PASS'; exit 0 }
'FINAL_RESULT=FAIL'
exit 1
