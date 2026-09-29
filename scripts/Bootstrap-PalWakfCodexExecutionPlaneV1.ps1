param(
    [string]$PackageSpec = "@openai/codex@alpha",
    [string]$StateDir = "C:\ProgramData\PalWakf\codex_execution_plane_v1\state"
)

$ErrorActionPreference = "Stop"

function Resolve-CommandPath([string[]]$Names) {
    foreach ($name in $Names) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($cmd -and $cmd.Source) { return $cmd.Source }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $StateDir)) {
    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
}

$node = Resolve-CommandPath @("node.exe","node")
if (-not $node) { throw "NODE_NOT_FOUND" }

$npm = Resolve-CommandPath @("npm.cmd","npm")
if (-not $npm) { throw "NPM_NOT_FOUND" }

$nodeVersion = (& $node --version).Trim()
if ($LASTEXITCODE -ne 0) { throw "NODE_VERSION_READBACK_FAILED" }

$npmVersion = (& $npm --version).Trim()
if ($LASTEXITCODE -ne 0) { throw "NPM_VERSION_READBACK_FAILED" }

& $npm install -g $PackageSpec
if ($LASTEXITCODE -ne 0) { throw "CODEX_INSTALL_FAILED" }

$codex = Resolve-CommandPath @("codex.cmd","codex.exe","codex")
if (-not $codex) { throw "CODEX_COMMAND_NOT_FOUND_AFTER_INSTALL" }

$codexVersion = (@(& $codex --version 2>&1) -join " ").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($codexVersion)) {
    throw "CODEX_VERSION_READBACK_FAILED"
}

$execHelp = @(& $codex exec-server --help 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw ("CODEX_EXEC_SERVER_NOT_AVAILABLE:" + ($execHelp -join " "))
}

$helpText = ($execHelp -join [Environment]::NewLine)
if ($helpText -notmatch "exec-server|environment-id|remote") {
    throw "CODEX_EXEC_SERVER_HELP_UNEXPECTED"
}

$evidence = [ordered]@{
    schema = "palwakf.codex_execution_plane.bootstrap_evidence.v1"
    created_at = [DateTime]::UtcNow.ToString("o")
    decision = "PASS"
    role = "PRIVILEGED_ENGINEERING_BOOTSTRAP_RECOVERY_PLANE"
    package_spec = $PackageSpec
    node_path = $node
    node_version = $nodeVersion
    npm_path = $npm
    npm_version = $npmVersion
    codex_path = $codex
    codex_version = $codexVersion
    exec_server_supported = $true
    credential_material_provisioned = $false
    credential_material_logged = $false
    next_gate = "PROVISION_SEPARATE_APPLICATION_AND_ENVIRONMENT_KEYS_OUT_OF_BAND"
    main_mutation = "NONE"
    baseline_mutation = "NONE"
    production_mutation = "NONE"
    shared_db_mutation = "NONE"
}

$evidencePath = Join-Path $StateDir "bootstrap-evidence.json"
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $evidencePath -Encoding UTF8

Write-Host "CODEX_BOOTSTRAP=PASS"
Write-Host ("CODEX_VERSION=" + $codexVersion)
Write-Host ("CODEX_PATH=" + $codex)
Write-Host "CODEX_EXEC_SERVER=AVAILABLE"
Write-Host ("EVIDENCE_PATH=" + $evidencePath)
Write-Host "NEXT_GATE=PROVISION_SEPARATE_APPLICATION_AND_ENVIRONMENT_KEYS_OUT_OF_BAND"
