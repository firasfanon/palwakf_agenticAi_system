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
    $EvidencePath = Join-Path $repoRoot ".venv-outbound-executor-v1\P3_RESILIENCE_PROOFS_HARDENED.log"
}
$firewallRule = "PalWakf-P3-Network-Loss-Proof-Hardened"

function Write-Evidence([string]$Message) {
    Add-Content -LiteralPath $EvidencePath -Value (([DateTime]::UtcNow.ToString("o")) + " " + $Message) -Encoding UTF8
}

function Get-ServicePid {
    $svc = Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $ServiceName } | Select-Object -First 1
    if (-not $svc) { return 0 }
    return [int]$svc.ProcessId
}

function Wait-ServicePidChange([int]$OldPid, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        $pidNow = Get-ServicePid
        if ($svc -and $svc.Status -eq "Running" -and $pidNow -gt 0 -and $pidNow -ne $OldPid) {
            return $pidNow
        }
    } while ((Get-Date) -lt $deadline)
    throw "SERVICE_PID_CHANGE_TIMEOUT"
}

function Assert-TransportHealth {
    $code = "import json; from palwakf_local_agents.outbound_worker_v1 import load_worker_config; from palwakf_local_agents.github_issue_transport_v1 import GitHubIssueTransportV1; c=load_worker_config(r'$ConfigPath'); print(json.dumps(GitHubIssueTransportV1(c.transport).health(), sort_keys=True))"
    $output = @(& $PythonExe -c $code 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw ("TRANSPORT_HEALTH_FAILED:" + ($output -join " "))
    }
    $joined = ($output -join "")
    if ($joined -notmatch '"status": "HEALTHY"') {
        throw ("TRANSPORT_HEALTH_NOT_HEALTHY:" + $joined)
    }
    return $joined
}

function Read-NewTransportEvents([int]$StartLine) {
    if (-not (Test-Path -LiteralPath $RuntimeAuditPath)) { return @() }
    $all = @(Get-Content -LiteralPath $RuntimeAuditPath -ErrorAction Stop)
    if ($all.Count -le $StartLine) { return @() }
    return @($all[$StartLine..($all.Count - 1)])
}

Remove-Item -LiteralPath $EvidencePath -Force -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue
Write-Evidence "HARNESS=PASS"

try {
    $svc = Get-CimInstance Win32_Service | Where-Object { $_.Name -eq $ServiceName } | Select-Object -First 1
    if (-not $svc) { throw "SERVICE_NOT_FOUND" }
    if ($svc.State -ne "Running") { throw ("SERVICE_NOT_RUNNING_PRE:" + $svc.State) }
    if ($svc.StartMode -ne "Auto") { throw ("SERVICE_NOT_AUTOMATIC_PRE:" + $svc.StartMode) }
    $health0 = Assert-TransportHealth
    Write-Evidence ("PREFLIGHT=PASS PID=" + $svc.ProcessId + " STARTMODE=" + $svc.StartMode + " TRANSPORT=" + $health0)

    $pid0 = [int]$svc.ProcessId
    Restart-Service -Name $ServiceName -Force -ErrorAction Stop
    $pid1 = Wait-ServicePidChange $pid0 90
    $health1 = Assert-TransportHealth
    Write-Evidence ("CONTROLLED_SERVICE_RESTART_PROOF=PASS OLD_PID=" + $pid0 + " NEW_PID=" + $pid1 + " TRANSPORT=" + $health1)

    $pid2 = Get-ServicePid
    Stop-Process -Id $pid2 -Force -ErrorAction Stop
    Write-Evidence ("PROCESS_KILL_INJECTED=TRUE KILLED_PID=" + $pid2)
    $pid3 = Wait-ServicePidChange $pid2 180
    Start-Sleep -Seconds 10
    $health2 = Assert-TransportHealth
    Write-Evidence ("PROCESS_KILL_RECOVERY_PROOF=PASS OLD_PID=" + $pid2 + " NEW_PID=" + $pid3 + " TRANSPORT=" + $health2)

    $auditStart = 0
    if (Test-Path -LiteralPath $RuntimeAuditPath) {
        $auditStart = @(Get-Content -LiteralPath $RuntimeAuditPath).Count
    }
    $networkPid = Get-ServicePid
    New-NetFirewallRule -DisplayName $firewallRule -Direction Outbound -Action Block -Service $ServiceName -Protocol TCP -RemotePort 443 | Out-Null
    Write-Evidence ("NETWORK_LOSS_INJECTED=TRUE PID=" + $networkPid + " AUDIT_START_LINE=" + $auditStart)

    $deadline = (Get-Date).AddSeconds(80)
    do {
        Start-Sleep -Seconds 5
        $s = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        $p = Get-ServicePid
        if (-not $s -or $s.Status -ne "Running" -or $p -ne $networkPid) {
            throw ("SERVICE_DIED_DURING_NETWORK_LOSS STATUS=" + $(if ($s) { $s.Status } else { "MISSING" }) + " PID=" + $p)
        }
    } while ((Get-Date) -lt $deadline)
    Write-Evidence ("NETWORK_LOSS_SERVICE_SURVIVAL=PASS PID=" + $networkPid)

    Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue
    Write-Evidence "NETWORK_RESTORED=TRUE"

    $recoveryDeadline = (Get-Date).AddSeconds(120)
    $sawError = $false
    $sawRecovery = $false
    do {
        Start-Sleep -Seconds 5
        $events = Read-NewTransportEvents $auditStart
        $joinedEvents = ($events -join "\n")
        if ($joinedEvents -match '"event": "TRANSPORT_ERROR"') { $sawError = $true }
        if ($joinedEvents -match '"event": "TRANSPORT_RECOVERED"') { $sawRecovery = $true }
        if ($sawError -and $sawRecovery) { break }
    } while ((Get-Date) -lt $recoveryDeadline)
    if (-not $sawError) { throw "NETWORK_LOSS_TRANSPORT_ERROR_NOT_OBSERVED" }
    if (-not $sawRecovery) { throw "NETWORK_RECONNECT_NOT_OBSERVED" }

    $finalPid = Get-ServicePid
    if ($finalPid -ne $networkPid) { throw ("PID_CHANGED_DURING_NETWORK_PROOF:" + $networkPid + "->" + $finalPid) }
    $health3 = Assert-TransportHealth
    Write-Evidence ("NETWORK_LOSS_RECONNECT_PROOF=PASS PID=" + $finalPid + " TRANSPORT=" + $health3)
    Write-Evidence "P3_RESILIENCE_PROOFS=PASS"
    exit 0
}
catch {
    Write-Evidence ("P3_RESILIENCE_PROOFS=FAIL ERROR=" + $_.Exception.Message)
    exit 1
}
finally {
    Remove-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue
}
