from pathlib import Path


def test_pre_reboot_closeout_contract():
    s=Path("scripts/Prepare-P3RuntimeCloseout.ps1").read_text(encoding="utf-8")
    for marker in [
        "AUTHORITATIVE_BOOTSTRAP=PASS",
        "CONTROLLED_SERVICE_RESTART_PROOF=PASS",
        "PROCESS_KILL_RECOVERY_PROOF=PASS",
        "NETWORK_LOSS_SERVICE_SURVIVAL=PASS",
        "NETWORK_LOSS_RECONNECT_PROOF=PASS",
        "P3_PRE_REBOOT_GATE=PASS",
        "NEXT_REQUIRED_ACTION=WINDOWS_RESTART",
    ]:
        assert marker in s
    assert "Restart-Computer" not in s


def test_post_reboot_closeout_contract():
    s=Path("scripts/Verify-P3RebootCloseout.ps1").read_text(encoding="utf-8")
    for marker in [
        "WINDOWS_REBOOT_NOT_PROVEN",
        "WINDOWS_REBOOT_RECOVERY_PROOF=PASS",
        "P3_RUNTIME_CLOSEOUT=PASS",
        "PALWAKF_P3_RUNTIME_CLOSEOUT_EVIDENCE_V1",
        "manual_terminal_interventions_per_task=0",
        'main_mutation="NONE"',
        'baseline_mutation="NONE"',
        'production_mutation="NONE"',
    ]:
        assert marker in s


def test_resilience_harness_uses_normalized_windows_paths():
    s=Path("scripts/Invoke-P3OutboundExecutorResilienceProofs.ps1").read_text(encoding="utf-8")
    assert 'C:\\\\Program Files' not in s
    assert 'C:\\\\ProgramData' not in s
    assert 'C:\\Program Files\\Python311\\python.exe' in s
