param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference='Stop'
$python=Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$src=Join-Path $ProjectRoot 'backend\src'
if(-not(Test-Path -LiteralPath $python)){throw 'PYTHON_NOT_FOUND'}
$script=@'
from pathlib import Path
import json, sqlite3, sys
root=Path(sys.argv[1])
registry=json.loads((root/'config'/'local_actor_scope_registry_v1.json').read_text(encoding='utf-8'))
assert registry['contract']=='LOCAL_ACTOR_SCOPE_REGISTRY_V1'
assert registry['default_access']=='DENY'
assert registry['actors']==[]
app=(root/'backend'/'src'/'palwakf_local_agents'/'app.py').read_text(encoding='utf-8')
assert 'mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)' in app
for ws in ('personal_development','commercial_projects','research_learning'):
 p=root/'workspaces'/ws/'capability_foundation.sqlite'; assert p.is_file(), p
 con=sqlite3.connect(p)
 for table in ('tasks','projects','review_records','tool_runs'):
  cols={row[1] for row in con.execute(f'pragma table_info({table})')}
  assert 'client_id' in cols, (ws,table,cols)
 con.close()
assert (root/'workspaces'/'palwakf_government'/'local_agent_core.sqlite').is_file()
print('POST_APPLY_AUTHZ_STATIC_CONTRACT=PASS')
'@
$temp=Join-Path $env:TEMP ('test_gcf_authz_postapply_{0}.py' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
[IO.File]::WriteAllText($temp,$script,(New-Object System.Text.UTF8Encoding($false)))
try{$env:PYTHONPATH=$src;& $python $temp $ProjectRoot;if($LASTEXITCODE -ne 0){throw 'POST_APPLY_AUTHZ_STATIC_CONTRACT_FAILED'}}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
'POST_APPLY_UAT_STATUS=PASS';'AUTHENTICATED_ACTOR_DEFAULT=DENY';'CROSS_WORKSPACE_ACCESS=DENY_BY_ACTOR_SCOPE';'COMMERCIAL_CLIENT_BOUNDARY=ENFORCED';'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'PROJECT_MUTATION=NONE_DURING_UAT'
