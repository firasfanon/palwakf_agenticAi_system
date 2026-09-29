param(
    [string]$ServiceName = "PalWakfOutboundLocalExecutorV1",
    [string]$PythonExe = "C:\Program Files\Python311\python.exe",
    [string]$ConfigPath = "C:\ProgramData\PalWakf\outbound_executor_v1\config.json",
    [string]$RuntimeAuditPath = "C:\ProgramData\PalWakf\outbound_executor_v1\state\transport-runtime.jsonl",
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot ".venv-outbound-executor-v1\P3_NETWORK_RECOVERY_REPAIR.log"
}
$firewallRule = "PalWakf-P3-Network-Loss-Proof-Program"

function E([string]$Message) {
    Add-Content -LiteralPath $EvidencePath -Value (([DateTime]::UtcNow.ToString("o")) + " " + $Message) -Encoding UTF8
}

function ServiceSnapshot {
    Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $ServiceName } | Select-Object -First 1
}

function Health {
    $code = "import json; from palwakf_local_agents.outbound_worker_v1 import load_worker_config; from palwakf_local_agents.github_issue_transport_v1 import GitHubIssueTransportV1; c=load_worker_config(r'$ConfigPath'); print(json.dumps(GitHubIssueTransportV1(c.transport).health(), sort_keys=True))"
    $output = @(& $PythonExe -c $code 2>&1)
    if ($LASTEXITCODE -ne 0) { throw ("TRANSPORT_HEALTH_FAILED:" + ($output -join " ")) }
    $joined = ($output -join "")
    if ($joined -notmatch '"status": "HEALTHY"') { throw ("TRANSPORT_NOT_HEALTHY:" + $joined) }
    return $joined
}

function NewEvents([int]$Start) {
    if (-not (Test-Path -LiteralPath $RuntimeAuditPath)) { return @() }
    $all = @(Get-Content -LiteralPath $RuntimeAuditPath -ErrorAction Stop)
    if ($all.Count -le $Start) { return @() }
    return @($all[$Start..($all.Count - 1)])
}

Remove-Item -LiteralPath $EvidencePath -Force -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue
E "NETWORK_REPAIR_HARNESS=PASS"

try {
    $svc = ServiceSnapshot
    if (-not $svc) { throw "SERVICE_NOT_FOUND" }
    if ($svc.State -ne "Running") { throw ("SERVICE_NOT_RUNNING:" + $svc.State) }
    if ($svc.StartMode -ne "Auto") { throw ("SERVICE_NOT_AUTO:" + $svc.StartMode) }

    $program = [Environment]::ExpandEnvironmentVariables([string]$svc.PathName).Trim('"')
    if (-not (Test-Path -LiteralPath $program -PathType Leaf)) { throw ("SERVICE_PROGRAM_NOT_FOUND:" + $program) }

    $beforeHealth = Health
    $pidBefore = [int]$svc.ProcessId
    $auditStart = 0
    if (Test-Path -LiteralPath $RuntimeAuditPath) {
        $auditStart = @(Get-Content -LiteralPath $RuntimeAuditPath).Count
    }

    E ("PREFLIGHT=PASS PID=" + $pidBefore + " PROGRAM=" + $program + " TRANSPORT=" + $beforeHealth)

    New-NetFirewallRule -DisplayName $firewallRule -Direction Outbound -Action Block -Program $program -Protocol TCP -RemotePort 443 -Profile Any | Out-Null

    $rule = Get-NetFirewallRule -DisplayName $firewallRule -ErrorAction Stop
    $filter = $rule | Get-NetFirewallApplicationFilter
    if ($rule.Enabled -ne "True" -and $rule.Enabled -ne $true) { throw "NETWORK_BLOCK_RULE_NOT_ENABLED" }
    if (-not [string]::Equals($filter.Program, $program, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw ("NETWORK_BLOCK_RULE_PROGRAM_MISMATCH:" + $filter.Program)
    }
    E ("NETWORK_LOSS_INJECTED=TRUE PID=" + $pidBefore + " PROGRAM=" + $program + " AUDIT_START_LINE=" + $auditStart)

    $errorDeadline = (Get-Date).AddSeconds(90)
    $sawError = $false
    do {
        Start-Sleep -Seconds 5
        $nowSvc = ServiceSnapshot
        if (-not $nowSvc -or $nowSvc.State -ne "Running") { throw "SERVICE_STOPPED_DURING_NETWORK_LOSS" }
        if ([int]$nowSvc.ProcessId -ne $pidBefore) { throw ("PID_CHANGED_DURING_NETWORK_LOSS:" + $pidBefore + "->" + $nowSvc.ProcessId) }
        $events = NewEvents $auditStart
        if (($events -join "\n") -match '"event": "TRANSPORT_ERROR"') {
            $sawError = $true
            break
        }
    } while ((Get-Date) -lt $errorDeadline)

    if (-not $sawError) { throw "NETWORK_LOSS_TRANSPORT_ERROR_NOT_OBSERVED_WITH_PROGRAM_BLOCK" }
    E ("NETWORK_LOSS_TRANSPORT_ERROR_OBSERVED=PASS PID=" + $pidBefore)
    E ("NETWORK_LOSS_SERVICE_SURVIVAL=PASS PID=" + $pidBefore)

    Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction Stop
    E "NETWORK_RESTORED=TRUE"

    $recoverDeadline = (Get-Date).AddSeconds(120)
    $sawRecovery = $false
    do {
        Start-Sleep -Seconds 5
        $nowSvc = ServiceSnapshot
        if (-not $nowSvc -or $nowSvc.State -ne "Running") { throw "SERVICE_STOPPED_DURING_RECONNECT" }
        if ([int]$nowSvc.ProcessId -ne $pidBefore) { throw ("PID_CHANGED_DURING_RECONNECT:" + $pidBefore + "->" + $nowSvc.ProcessId) }
        $events = NewEvents $auditStart
        if (($events -join "\n") -match '"event": "TRANSPORT_RECOVERED"') {
            $sawRecovery = $true
            break
        }
    } while ((Get-Date) -lt $recoverDeadline)

    if (-not $sawRecovery) { throw "NETWORK_RECONNECT_NOT_OBSERVED" }

    $afterHealth = Health
    E ("NETWORK_LOSS_RECONNECT_PROOF=PASS PID=" + $pidBefore + " TRANSPORT=" + $afterHealth)
    E "P3_NETWORK_RECOVERY_REPAIR=PASS"
    exit 0
}
catch {
    E ("P3_NETWORK_RECOVERY_REPAIR=FAIL ERROR=" + $_.Exception.Message)
    exit 1
}
finally {
    Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue
}
