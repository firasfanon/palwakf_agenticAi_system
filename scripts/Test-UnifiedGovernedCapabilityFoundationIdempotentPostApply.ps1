param(
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference='Stop'
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python -PathType Leaf)){throw 'PYTHON_NOT_FOUND'}
$temp=Join-Path $env:TEMP ("verify_idempotent_gcf_postapply_{0}.py" -f (Get-Date -Format 'yyyyMMdd_HHmmssfff'))
$code=@'
from pathlib import Path
import json, sqlite3, sys
root=Path(sys.argv[1])
app=(root/'backend'/'src'/'palwakf_local_agents'/'app.py').read_text(encoding='utf-8')
assert app.count('from .governed_capability_foundation import mount_governed_capability_foundation') == 1
assert app.count('mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)') == 1
assert (root/'workspaces'/'palwakf_government'/'workspace_manifest.json').is_file()
assert (root/'workspaces'/'palwakf_government'/'local_agent_core.sqlite').is_file()
for ws in ('personal_development','commercial_projects','research_learning'):
    db=root/'workspaces'/ws/'capability_foundation.sqlite'
    assert db.is_file(), db
    con=sqlite3.connect(db)
    tables={row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    assert {'schema_migrations','tasks','projects','review_records','tool_runs','audit_events'}.issubset(tables)
    assert con.execute("select count(*) from schema_migrations where version='GOVERNED_CAPABILITY_FOUNDATION_V1'").fetchone()[0] == 1
    con.close()
config=json.loads((root/'config'/'controlled_first_prompt_pilot_v1.json').read_text(encoding='utf-8'))
assert config['execution']['model_execution']=='NONE_UNTIL_SEPARATE_EXPLICIT_RUNTIME_AUTHORIZATION'
assert config['execution']['allowed_tools']=='NONE'
print('POST_APPLY_IDEMPOTENT_STATIC_CONTRACT=PASS')
'@
[System.IO.File]::WriteAllText($temp,$code,(New-Object System.Text.UTF8Encoding($false)))
try{& $python $temp $ProjectRoot;if($LASTEXITCODE -ne 0){throw 'POST_APPLY_STATIC_CONTRACT_FAILED'}}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
'POST_APPLY_UAT_STATUS=PASS'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'PROJECT_MUTATION=NONE_DURING_UAT'
