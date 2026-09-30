from __future__ import annotations

import re
from pathlib import Path

import pytest


SOURCE = (
    Path(__file__).resolve().parents[2]
    / "scripts/Test-PalWakfCodexExecutionPlaneReadinessV1.ps1"
).read_text(encoding="utf-8")


def test_readiness_binds_repository_branch_head_tree_and_clean_tracked_state():
    assert "[string]$ExpectedHead" in SOURCE
    assert "[string]$ExpectedTree" in SOURCE
    assert (
        r"[string]$RepoRoot = 'C:\Users\DELL\StudioProjects\palwakf_agenticAi_system'"
        in SOURCE
    )
    assert "$governedBranch = 'task/AGENTIC-CODEX-EXECUTION-PLANE-ADMISSION-V1'" in SOURCE
    assert "GetFullPath($RepoRoot).TrimEnd('\\') -cne $governedRoot" in SOURCE
    assert "rev-parse --show-toplevel" in SOURCE
    assert "branch --show-current" in SOURCE
    assert "rev-parse HEAD" in SOURCE
    assert "rev-parse 'HEAD^{tree}'" in SOURCE
    assert "status --porcelain=v1 --untracked-files=no" in SOURCE
    assert "$result.BRANCH -cne $governedBranch" in SOURCE
    assert "$result.HEAD -ine $ExpectedHead" in SOURCE
    assert "$result.TREE -ine $ExpectedTree" in SOURCE
    assert "$result.TRACKED_STATUS -cne 'CLEAN'" in SOURCE
    assert "throw 'REPOSITORY_BINDING_MISMATCH'" in SOURCE
    assert SOURCE.index("throw 'REPOSITORY_BINDING_MISMATCH'") < SOURCE.index("& $codex --version")


def test_readiness_only_invokes_installed_codex_informational_commands():
    assert "Get-Command $name -CommandType Application, ExternalScript" in SOURCE
    assert "@('codex.exe', 'codex.cmd', 'codex')" in SOURCE
    calls = re.findall(r"& \$codex ([^\r\n]+)", SOURCE)
    assert calls == ["--version 2>&1)", "exec-server --help 2>&1)"]
    assert "if ($LASTEXITCODE -ne 0) { throw 'CODEX_EXEC_SERVER_UNAVAILABLE' }" in SOURCE
    assert "$result.CODEX_EXEC_SERVER = 'AVAILABLE'" in SOURCE


def test_readiness_reads_only_connection_metadata_and_validates_binding_identity():
    assert r"$runtimeRoot = 'C:\Users\DELL\AppData\Local\PalWakf\codex_execution_plane_v1'" in SOURCE
    assert r"$connectionPath = Join-Path $runtimeRoot 'state\connection.json'" in SOURCE
    assert "Get-Content -LiteralPath $connectionPath -Raw | ConvertFrom-Json" in SOURCE
    assert SOURCE.count("Get-Content") == 1
    assert "$connection.branch -cne $governedBranch" in SOURCE
    for field in ("head", "tree"):
        assert rf"$connection.{field} -cnotmatch '\A[0-9a-fA-F]{{40}}\z'" in SOURCE
        assert not re.search(rf"\$connection\.{field}\s+-[ci]?(?:eq|ne)\s+\$(?:Expected|result)", SOURCE, re.I)
    assert "IsNullOrWhiteSpace($connection.environment_id)" in SOURCE
    assert ".StartsWith('https://api.openai.com/v1/agents/api/connect/', [StringComparison]::Ordinal)" in SOURCE


@pytest.mark.parametrize(
    ("variable", "relative_path"),
    [
        ("launcherPath", "Start-PalWakfCodexExecServer.ps1"),
        ("dpapiKeyPath", r"secrets\environment-key.dpapi"),
        ("dpapiEntropyPath", r"secrets\environment-key.entropy"),
    ],
)
def test_readiness_sensitive_artifacts_are_existence_only(variable, relative_path):
    assert f"${variable} = Join-Path $runtimeRoot '{relative_path}'" in SOURCE
    assert f"Test-Path -LiteralPath ${variable} -PathType Leaf" in SOURCE
    # Each path is used exactly twice: its declaration and its existence check.
    assert len(re.findall(rf"\${variable}\b", SOURCE)) == 2


def test_readiness_uses_process_command_line_metadata_without_emitting_it():
    assert "Get-CimInstance -ClassName Win32_Process -Property CommandLine" in SOURCE
    assert '[regex]::Escape($connection.environment_id)' in SOURCE
    assert "$process.CommandLine -cmatch $environmentPattern" in SOURCE
    assert "exec-server(?=$|" in SOURCE
    assert not re.search(r"(?:Write-\w+|Out-\w+).*\$(?:process|connection)\b", SOURCE, re.I)


@pytest.mark.parametrize(
    "forbidden",
    [
        r"ReadAllBytes|ReadAllText|OpenRead|Get-FileHash|ComputeHash",
        r"ProtectedData\s*\]\s*::\s*Unprotect|ProtectedData\.Unprotect",
        r"CODEX_API_KEY|OPENAI_API_KEY",
        r"\$env:|\benv:|GetEnvironmentVariable|\.Environment(?:Variables)?\b",
        r"Get-Process|Get-WmiObject|Get-CimAssociatedInstance",
        r"\b(?:npm|pip|pip3|winget|choco)\s+(?:install|upgrade|update)\b|Install-Package",
        r"\b(?:git|\$git)\b[^\r\n]*(?:\b(?:add|commit|push|fetch|pull|merge|rebase|reset|checkout|switch|cherry-pick|clean|restore|update-ref)\b)",
        r"Set-Content|Add-Content|Out-File|New-Item|Remove-Item|Copy-Item|Move-Item|WriteAll|Start-Process|Invoke-Expression",
        r">\s*(?!&)[\w$'\"]",
    ],
)
def test_readiness_has_no_secret_access_installation_or_mutation(forbidden):
    assert not re.search(forbidden, SOURCE, re.I)


def test_readiness_emits_complete_fail_closed_stdout_contract():
    block = SOURCE.split("$result = [ordered]@{", 1)[1].split("\n}", 1)[0]
    defaults = dict(re.findall(r"^\s+(\w+) = '([^']*)'", block, re.M))
    assert list(defaults) == [
        "DECISION", "REPOSITORY", "BRANCH", "HEAD", "TREE", "TRACKED_STATUS",
        "CODEX_VERSION", "CODEX_EXEC_SERVER", "CONNECTION_STATE_FILE", "LAUNCHER_FILE",
        "DPAPI_KEY_FILE_EXISTS", "DPAPI_ENTROPY_FILE_EXISTS", "SECRET_CONTENT_ACCESSED",
        "REMOTE_URL_CONTRACT", "ENVIRONMENT_ID_PRESENT", "EXEC_SERVER_PROCESS", "MUTATION_PERFORMED",
    ]
    assert defaults["DECISION"] == "FAIL"
    for field in ("SECRET_CONTENT_ACCESSED", "MUTATION_PERFORMED"):
        assert f"{field}={defaults[field]}" == f"{field}=FALSE"
        assert not re.search(rf"\$result\.{field}\s*=", SOURCE, re.I)
    assert "Write-Output 'PALWAKF_CODEX_EXECUTION_PLANE_READINESS_V1'" in SOURCE
    assert "Write-Output ('{0}={1}' -f $field.Key, $field.Value)" in SOURCE
    assert "if ($result.DECISION -ceq 'PASS') { exit 0 }\nexit 1" in SOURCE
    assert "} catch {" in SOURCE
