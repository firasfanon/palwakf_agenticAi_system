param(
    [Parameter(Mandatory=$true)][string]$ExpectedHead,
    [Parameter(Mandatory=$true)][string]$ExpectedTree,
    [string]$RepoRoot = "C:\Users\DELL\StudioProjects\palwakf_agenticAi_system",
    [string]$PythonExe = "C:\Program Files\Python311\python.exe",
    [string]$ConfigPath = "C:\ProgramData\PalWakf\outbound_executor_v1\config.json"
)
$ErrorActionPreference = "Stop"
$ServiceName = "PalWakfOutboundLocalExecutorV1"
$RuntimeDir = Join-Path $RepoRoot ".venv-outbound-executor-v1"
$MasterLog = Join-Path $RuntimeDir "P3_CLOSEOUT_PRE_REBOOT.log"
$ResilienceLog = Join-Path $RuntimeDir "P3_RESILIENCE_PROOFS_HARDENED.log"
$MarkerDir = "C:\ProgramData\PalWakf\outbound_executor_v1\state"
$MarkerPath = Join-Path $MarkerDir "p3-reboot-proof-marker.json"

function L([string]$m) {
    if (-not (Test-Path -LiteralPath $RuntimeDir)) { New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null }
    Add-Content -LiteralPath $MasterLog -Value (([DateTime]::UtcNow.ToString("o")) + " " + $m) -Encoding UTF8
}
function GitReality {
    Set-Location $RepoRoot
    $b=(& git branch --show-current).Trim()
    $h=(& git rev-parse HEAD).Trim()
    $t=(& git rev-parse "HEAD^{tree}").Trim()
    if($b -ne "task/AGENTIC-P3-OUTBOUND-LOCAL-EXECUTOR-V1"){throw "BRANCH_MISMATCH:$b"}
    if($h -ne $ExpectedHead){throw "HEAD_MISMATCH:$h"}
    if($t -ne $ExpectedTree){throw "TREE_MISMATCH:$t"}
    [pscustomobject]@{Branch=$b;Head=$h;Tree=$t}
}

Remove-Item -LiteralPath $MasterLog -Force -ErrorAction SilentlyContinue
try {
    $g=GitReality
    L ("GIT_REALITY=PASS HEAD="+$g.Head+" TREE="+$g.Tree)

    $boot=Join-Path $RepoRoot "scripts\Bootstrap-PalWakfOutboundLocalExecutorV1.ps1"
    $bo=@(& $boot -RepoRoot $RepoRoot -ConfigPath $ConfigPath -MachinePythonExe $PythonExe 2>&1)
    if($LASTEXITCODE -ne 0){throw ("BOOTSTRAP_FAILED:"+($bo -join " | "))}

    $svc=Get-CimInstance Win32_Service | Where-Object {$_.Name -eq $ServiceName} | Select-Object -First 1
    if(-not $svc -or $svc.State -ne "Running" -or $svc.StartMode -ne "Auto"){throw "SERVICE_BOOTSTRAP_GATE_FAILED"}
    L ("AUTHORITATIVE_BOOTSTRAP=PASS PID="+$svc.ProcessId)

    $res=Join-Path $RepoRoot "scripts\Invoke-P3OutboundExecutorResilienceProofs.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $res -EvidencePath $ResilienceLog
    if($LASTEXITCODE -ne 0){throw "RESILIENCE_PROOFS_FAILED"}
    $txt=Get-Content -LiteralPath $ResilienceLog -Raw
    foreach($m in @("CONTROLLED_SERVICE_RESTART_PROOF=PASS","PROCESS_KILL_RECOVERY_PROOF=PASS","NETWORK_LOSS_SERVICE_SURVIVAL=PASS","NETWORK_LOSS_RECONNECT_PROOF=PASS","P3_RESILIENCE_PROOFS=PASS")){
        if($txt -notmatch [regex]::Escape($m)){throw ("MISSING_RESILIENCE_MARKER:"+$m)}
    }
    L "PROCESS_NETWORK_RESILIENCE=PASS"

    if(-not (Test-Path -LiteralPath $MarkerDir)){New-Item -ItemType Directory -Force -Path $MarkerDir | Out-Null}
    $svc2=Get-CimInstance Win32_Service | Where-Object {$_.Name -eq $ServiceName} | Select-Object -First 1
    [pscustomobject]@{
        schema="palwakf.p3.reboot_marker.v1"
        created_at=[DateTime]::UtcNow.ToString("o")
        boot_before=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString("o")
        service_pid_before=[int]$svc2.ProcessId
        expected_head=$ExpectedHead
        expected_tree=$ExpectedTree
        resilience_sha256=(Get-FileHash -LiteralPath $ResilienceLog -Algorithm SHA256).Hash.ToLowerInvariant()
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $MarkerPath -Encoding UTF8
    L "P3_PRE_REBOOT_GATE=PASS"
    L "NEXT_REQUIRED_ACTION=WINDOWS_RESTART"
    exit 0
} catch {
    L ("P3_PRE_REBOOT_GATE=FAIL ERROR="+$_.Exception.Message)
    exit 1
}
