[CmdletBinding()]
param(
    [string]$ExpectedHead,
    [string]$ExpectedTree,
    [string]$RepoRoot = 'C:\Users\DELL\StudioProjects\palwakf_agenticAi_system'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$governedRoot = 'C:\Users\DELL\StudioProjects\palwakf_agenticAi_system'
$governedBranch = 'task/AGENTIC-CODEX-EXECUTION-PLANE-ADMISSION-V1'
$runtimeRoot = 'C:\Users\DELL\AppData\Local\PalWakf\codex_execution_plane_v1'
$connectionPath = Join-Path $runtimeRoot 'state\connection.json'
$launcherPath = Join-Path $runtimeRoot 'Start-PalWakfCodexExecServer.ps1'
$dpapiKeyPath = Join-Path $runtimeRoot 'secrets\environment-key.dpapi'
$dpapiEntropyPath = Join-Path $runtimeRoot 'secrets\environment-key.entropy'

# Unknown checks retain their fail-closed values. Never emit native diagnostics
# or process command lines; only the bounded readiness fields go to stdout.
$result = [ordered]@{
    DECISION = 'FAIL'
    REPOSITORY = ''
    BRANCH = ''
    HEAD = ''
    TREE = ''
    TRACKED_STATUS = 'DIRTY'
    CODEX_VERSION = ''
    CODEX_EXEC_SERVER = 'UNAVAILABLE'
    CONNECTION_STATE_FILE = 'FAIL'
    LAUNCHER_FILE = 'FAIL'
    DPAPI_KEY_FILE_EXISTS = 'FALSE'
    DPAPI_ENTROPY_FILE_EXISTS = 'FALSE'
    SECRET_CONTENT_ACCESSED = 'FALSE'
    REMOTE_URL_CONTRACT = 'FAIL'
    ENVIRONMENT_ID_PRESENT = 'FALSE'
    EXEC_SERVER_PROCESS = 'NOT_RUNNING'
    MUTATION_PERFORMED = 'FALSE'
}

try {
    if ($ExpectedHead -cnotmatch '\A[0-9a-fA-F]{40}\z' -or
        $ExpectedTree -cnotmatch '\A[0-9a-fA-F]{40}\z') {
        throw 'EXPECTED_IDENTITY_INVALID'
    }
    if ([System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\') -cne $governedRoot) {
        throw 'REPOSITORY_PATH_MISMATCH'
    }
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).ProviderPath
    if ($RepoRoot -cne $governedRoot) { throw 'REPOSITORY_PATH_MISMATCH' }
    $git = (Get-Command git.exe -CommandType Application -ErrorAction Stop).Source
    $repository = @(& $git -C $RepoRoot rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0 -or $repository.Count -ne 1 -or
        ([string]$repository[0]).Replace('/', '\') -cne $governedRoot) {
        throw 'REPOSITORY_ROOT_MISMATCH'
    }
    $result.REPOSITORY = $governedRoot
    $branch = @(& $git -C $RepoRoot branch --show-current 2>&1)
    if ($LASTEXITCODE -ne 0 -or $branch.Count -ne 1) { throw 'BRANCH_READ_FAILED' }
    $result.BRANCH = [string]$branch[0]
    $head = @(& $git -C $RepoRoot rev-parse HEAD 2>&1)
    if ($LASTEXITCODE -ne 0 -or $head.Count -ne 1) { throw 'HEAD_READ_FAILED' }
    $result.HEAD = [string]$head[0]
    $tree = @(& $git -C $RepoRoot rev-parse 'HEAD^{tree}' 2>&1)
    if ($LASTEXITCODE -ne 0 -or $tree.Count -ne 1) { throw 'TREE_READ_FAILED' }
    $result.TREE = [string]$tree[0]
    $trackedStatus = @(& $git -C $RepoRoot status --porcelain=v1 --untracked-files=no 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'TRACKED_STATUS_READ_FAILED' }
    if ($trackedStatus.Count -eq 0) { $result.TRACKED_STATUS = 'CLEAN' }
    if ($result.BRANCH -cne $governedBranch -or
        $result.HEAD -ine $ExpectedHead -or $result.TREE -ine $ExpectedTree -or
        $result.TRACKED_STATUS -cne 'CLEAN') {
        throw 'REPOSITORY_BINDING_MISMATCH'
    }

    # Resolve an installed CLI only. Both invocations are informational.
    $codex = $null
    foreach ($name in @('codex.exe', 'codex.cmd', 'codex')) {
        $command = Get-Command $name -CommandType Application, ExternalScript -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($command) { $codex = $command.Source; break }
    }
    if (-not $codex) { throw 'CODEX_NOT_INSTALLED' }
    $version = @(& $codex --version 2>&1)
    if ($LASTEXITCODE -ne 0 -or $version.Count -ne 1 -or
        [string]$version[0] -cnotmatch '\Acodex-cli [0-9][0-9A-Za-z.+-]*\z') {
        throw 'CODEX_VERSION_FAILED'
    }
    $result.CODEX_VERSION = [string]$version[0]
    $null = @(& $codex exec-server --help 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'CODEX_EXEC_SERVER_UNAVAILABLE' }
    $result.CODEX_EXEC_SERVER = 'AVAILABLE'

    # Existence only: never open the launcher or either protected secret file.
    $connectionExists = Test-Path -LiteralPath $connectionPath -PathType Leaf
    if (Test-Path -LiteralPath $launcherPath -PathType Leaf) { $result.LAUNCHER_FILE = 'PASS' }
    if (Test-Path -LiteralPath $dpapiKeyPath -PathType Leaf) { $result.DPAPI_KEY_FILE_EXISTS = 'TRUE' }
    if (Test-Path -LiteralPath $dpapiEntropyPath -PathType Leaf) { $result.DPAPI_ENTROPY_FILE_EXISTS = 'TRUE' }
    if (-not $connectionExists) { throw 'CONNECTION_STATE_MISSING' }

    $connection = Get-Content -LiteralPath $connectionPath -Raw | ConvertFrom-Json
    # These SHAs identify the original connection binding, not the current commit.
    if ($connection.branch -isnot [string] -or $connection.branch -cne $governedBranch -or
        $connection.head -isnot [string] -or $connection.head -cnotmatch '\A[0-9a-fA-F]{40}\z' -or
        $connection.tree -isnot [string] -or $connection.tree -cnotmatch '\A[0-9a-fA-F]{40}\z') {
        throw 'CONNECTION_BINDING_INVALID'
    }
    if ($connection.environment_id -is [string] -and
        -not [string]::IsNullOrWhiteSpace($connection.environment_id)) {
        $result.ENVIRONMENT_ID_PRESENT = 'TRUE'
    }
    if ($connection.remote_url -is [string] -and
        $connection.remote_url.StartsWith('https://api.openai.com/v1/agents/api/connect/', [StringComparison]::Ordinal)) {
        $result.REMOTE_URL_CONTRACT = 'PASS'
    }
    if ($result.ENVIRONMENT_ID_PRESENT -cne 'TRUE' -or $result.REMOTE_URL_CONTRACT -cne 'PASS') {
        throw 'CONNECTION_CONTRACT_INVALID'
    }
    $result.CONNECTION_STATE_FILE = 'PASS'

    # Request command-line metadata only and never output it. Token boundaries
    # prevent accepting a different environment whose ID merely shares a prefix.
    $environmentPattern = '(?:^|[\s"''=])' + [regex]::Escape($connection.environment_id) + '(?=$|[\s"''])'
    $processes = Get-CimInstance -ClassName Win32_Process -Property CommandLine -Filter "Name = 'codex.exe'"
    foreach ($process in $processes) {
        if ($process.CommandLine -and
            $process.CommandLine -match '(?:^|[\s"''])exec-server(?=$|[\s"''])' -and
            $process.CommandLine -cmatch $environmentPattern) {
            $result.EXEC_SERVER_PROCESS = 'RUNNING'
            break
        }
    }
    if ($result.LAUNCHER_FILE -ceq 'PASS' -and
        $result.DPAPI_KEY_FILE_EXISTS -ceq 'TRUE' -and
        $result.DPAPI_ENTROPY_FILE_EXISTS -ceq 'TRUE' -and
        $result.EXEC_SERVER_PROCESS -ceq 'RUNNING') {
        $result.DECISION = 'PASS'
    }
} catch {
    # Intentionally omit exception text: native diagnostics are outside the
    # secret-free output contract. Defaults and completed checks identify failure.
    $result.DECISION = 'FAIL'
}

Write-Output 'PALWAKF_CODEX_EXECUTION_PLANE_READINESS_V1'
foreach ($field in $result.GetEnumerator()) {
    Write-Output ('{0}={1}' -f $field.Key, $field.Value)
}
if ($result.DECISION -ceq 'PASS') { exit 0 }
exit 1
