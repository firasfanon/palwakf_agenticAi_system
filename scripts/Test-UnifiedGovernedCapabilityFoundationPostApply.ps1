param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$src=Join-Path $ProjectRoot 'backend\src'
if(-not(Test-Path -LiteralPath $python)){throw 'PYTHON_NOT_FOUND'}
$script=@'
from pathlib import Path
import json, sqlite3, sys
root=Path(sys.argv[1])
assert (root/'workspaces'/'palwakf_government'/'workspace_manifest.json').is_file()
assert (root/'workspaces'/'palwakf_government'/'local_agent_core.sqlite').is_file()
assert (root/'evidence'/'ledger'/'ledger_contract.json').is_file()
for ws in ('personal_development','commercial_projects','research_learning'):
    p=root/'workspaces'/ws/'capability_foundation.sqlite'
    assert p.is_file(), p
    con=sqlite3.connect(p)
    assert con.execute("select count(*) from schema_migrations").fetchone()[0] == 1
    con.close()
config=json.loads((root/'config'/'controlled_first_prompt_pilot_v1.json').read_text(encoding='utf-8'))
assert config['pilot_workspace_id']=='research_learning'
assert config['human_reviewer']=='Firas_Fanon'
assert config['execution']['model_execution']=='NONE_UNTIL_SEPARATE_EXPLICIT_RUNTIME_AUTHORIZATION'
print('POST_APPLY_STATIC_CONTRACT=PASS')
'@
$temp=Join-Path $env:TEMP ("test_unified_governed_capability_foundation_{0}.py" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
[System.IO.File]::WriteAllText($temp,$script,(New-Object System.Text.UTF8Encoding($false)))
try{$env:PYTHONPATH=$src;& $python $temp $ProjectRoot;if($LASTEXITCODE -ne 0){throw 'POST_APPLY_STATIC_CONTRACT_FAILED'}}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
'POST_APPLY_UAT_STATUS=PASS';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'PROJECT_MUTATION=NONE_DURING_UAT'
