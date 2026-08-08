[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$scope = Join-Path $root 'command_center'
if (-not (Test-Path -LiteralPath $scope -PathType Container)) { throw "COMMAND_CENTER_SCOPE_NOT_FOUND=$scope" }

$required = @(
  'command_center/__init__.py',
  'command_center/models.py',
  'command_center/read_only_store.py',
  'command_center/router.py',
  'command_center/static/index.html',
  'command_center/static/styles.css',
  'command_center/static/app.js'
)
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $root $_) -PathType Leaf) })
$text = Get-ChildItem -LiteralPath $scope -Recurse -File | Get-Content -Raw -Encoding UTF8
$forbidden = @('subprocess', 'ollama', 'requests.', 'httpx.', 'sqlalchemy', 'psycopg', 'git ', 'os.system', 'Popen(', 'POST', 'PUT', 'PATCH', 'DELETE', 'dotenv', 'load_dotenv')
$hits = @($forbidden | Where-Object { $text -match [regex]::Escape($_) })

"REQUIRED_FILE_COUNT=$($required.Count)"
"MISSING_FILE_COUNT=$($missing.Count)"
"MISSING_FILES=$($missing -join ';')"
"FORBIDDEN_TOKEN_HIT_COUNT=$($hits.Count)"
"FORBIDDEN_TOKEN_HITS=$($hits -join ';')"
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
'MEMORY_WRITE=NONE'
if ($missing.Count -eq 0 -and $hits.Count -eq 0) { 'FINAL_RESULT=PASS'; exit 0 }
'FINAL_RESULT=FAIL'
exit 1
