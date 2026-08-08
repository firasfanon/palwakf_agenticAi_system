param(
  [Parameter(Mandatory=$true)][string]$ProjectRoot
)
$ErrorActionPreference = 'Stop'
$python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$backend = Join-Path $ProjectRoot 'backend'
$src = Join-Path $backend 'src'
if(-not (Test-Path -LiteralPath $python -PathType Leaf)){ throw 'PYTHON_NOT_FOUND' }
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$evidence = Join-Path $env:TEMP ('final_consolidated_execution_carrier_post_apply_uat_{0}' -f $stamp)
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$script = @'
from pathlib import Path
import ast, json, sqlite3, sys
from fastapi import HTTPException
root = Path(sys.argv[1])
src = root / 'backend' / 'src'
sys.path.insert(0, str(src))
for p in (src / 'palwakf_local_agents' / 'governed_capability_foundation').rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'))
app_text = (src / 'palwakf_local_agents' / 'app.py').read_text(encoding='utf-8')
assert 'mount_governed_capability_foundation(app, project_root=PROJECT_ROOT)' in app_text
registry = json.loads((root / 'config' / 'local_actor_scope_registry_v1.json').read_text(encoding='utf-8'))
assert registry['default_access'] == 'DENY' and registry['actors'] == []
from palwakf_local_agents.governed_capability_foundation.authz import ActorPrincipal, require_commercial_client_scope, require_workspace_scope
actor = ActorPrincipal('scope_test_actor', frozenset({'research_learning'}), frozenset({'read'}), frozenset())
try:
    require_workspace_scope(actor, 'commercial_projects', 'read')
    raise AssertionError('cross_workspace_scope_not_denied')
except HTTPException as exc:
    assert exc.status_code == 403 and exc.detail['code'] == 'WORKSPACE_SCOPE_DENIED'
try:
    require_commercial_client_scope(actor, 'client_unassigned')
    raise AssertionError('commercial_client_scope_not_denied')
except HTTPException as exc:
    assert exc.status_code == 403 and exc.detail['code'] == 'COMMERCIAL_CLIENT_SCOPE_DENIED'
for workspace_id in ('personal_development','commercial_projects','research_learning'):
    db = root / 'workspaces' / workspace_id / 'capability_foundation.sqlite'
    assert db.is_file(), db
    con = sqlite3.connect(db)
    for table in ('tasks','projects','review_records','tool_runs','audit_events'):
        cols = {row[1] for row in con.execute(f'pragma table_info({table})')}
        assert cols, (workspace_id, table)
    con.close()
assert (root / 'workspaces' / 'palwakf_government' / 'local_agent_core.sqlite').is_file()
print('POST_APPLY_STATIC_AND_SCOPE_CONTRACT=PASS')
'@
$temp = Join-Path $evidence 'post_apply_static.py'
[System.IO.File]::WriteAllText($temp,$script,(New-Object System.Text.UTF8Encoding($false)))
$staticOutput = @()
try {
  $env:PYTHONPATH = $src
  $staticOutput = @(& $python $temp $ProjectRoot 2>&1)
  $staticOutput | Set-Content -LiteralPath (Join-Path $evidence 'static_contract.txt') -Encoding UTF8
  if($LASTEXITCODE -ne 0){ throw 'POST_APPLY_STATIC_CONTRACT_FAILED' }
}
finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }

$port = 8026
if(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue){ throw ('UAT_PORT_ALREADY_IN_USE={0}' -f $port) }
$stdout = Join-Path $evidence 'uvicorn_stdout.txt'
$stderr = Join-Path $evidence 'uvicorn_stderr.txt'
$server = $null
try {
  $server = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','palwakf_local_agents.app:app','--host','127.0.0.1','--port',"$port",'--log-level','warning') -WorkingDirectory $backend -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  $deadline = (Get-Date).AddSeconds(45)
  $health = $null
  while((Get-Date) -lt $deadline){
    try {
      $health = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/api/v1/governed-capability-foundation/health" -f $port) -UseBasicParsing -TimeoutSec 5
      if($health.StatusCode -eq 200){ break }
    }
    catch { Start-Sleep -Milliseconds 500 }
  }
  if($null -eq $health -or $health.StatusCode -ne 200){ throw 'GOVERNED_CAPABILITY_HEALTH_TIMEOUT' }
  $unauth = $null
  try { $null = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/api/v1/governed-capability-foundation/workspaces/research_learning/status" -f $port) -UseBasicParsing -TimeoutSec 10 }
  catch { $unauth = $_.Exception.Response }
  if($null -eq $unauth -or [int]$unauth.StatusCode -ne 401){ throw 'RUNTIME_DEFAULT_DENY_NOT_PROVEN' }
}
finally {
  if($server -and -not $server.HasExited){ Stop-Process -Id $server.Id -Force; Wait-Process -Id $server.Id -ErrorAction SilentlyContinue }
}
$archive = "$evidence.zip"
Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$evidence\*" -DestinationPath $archive -Force
'POST_APPLY_STATIC_CONTRACT=PASS'
'POST_APPLY_CROSS_WORKSPACE_SCOPE_CONTRACT=PASS'
'POST_APPLY_COMMERCIAL_CLIENT_SCOPE_CONTRACT=PASS'
'POST_APPLY_RUNTIME_DEFAULT_DENY_UAT=PASS'
('EVIDENCE_ARCHIVE={0}' -f $archive)
'UVICORN_PORT_8026=STOPPED'
'MODEL_EXECUTION=NONE';'PILOT_EXECUTION=NOT_EXECUTED';'SHELL_EXECUTION=NONE';'GIT_WRITE=NONE';'PROJECT_MUTATION=NONE_DURING_UAT'
