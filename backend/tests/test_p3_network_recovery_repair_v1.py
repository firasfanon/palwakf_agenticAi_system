from pathlib import Path


def test_program_scoped_firewall_is_used_for_network_loss_proof():
    full = Path("scripts/Invoke-P3OutboundExecutorResilienceProofs.ps1").read_text(encoding="utf-8")
    repair = Path("scripts/Invoke-P3NetworkRecoveryRepair.ps1").read_text(encoding="utf-8")
    for source in (full, repair):
        assert "-Program $serviceProgram" in source or "-Program $program" in source
        assert "Get-NetFirewallApplicationFilter" in source
        assert "-Service $ServiceName -Protocol TCP -RemotePort 443" not in source


def test_network_repair_requires_observed_error_and_recovery_without_pid_change():
    s = Path("scripts/Invoke-P3NetworkRecoveryRepair.ps1").read_text(encoding="utf-8")
    for marker in [
        "NETWORK_LOSS_TRANSPORT_ERROR_OBSERVED=PASS",
        "NETWORK_LOSS_SERVICE_SURVIVAL=PASS",
        "NETWORK_LOSS_RECONNECT_PROOF=PASS",
        "P3_NETWORK_RECOVERY_REPAIR=PASS",
        "PID_CHANGED_DURING_NETWORK_LOSS",
        "PID_CHANGED_DURING_RECONNECT",
    ]:
        assert marker in s
