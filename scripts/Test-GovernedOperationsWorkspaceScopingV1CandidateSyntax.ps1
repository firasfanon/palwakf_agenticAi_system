[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
function Fail([string]$Message){throw $Message}
if(-not (Test-Path -LiteralPath $PackageRoot -PathType Container)){Fail "PACKAGE_ROOT_NOT_FOUND=$PackageRoot"}
$pythonCommand=Get-Command python -ErrorAction SilentlyContinue
if($null -eq $pythonCommand){Fail 'PYTHON_COMMAND_NOT_FOUND'}
$pythonFiles=Get-ChildItem -LiteralPath $PackageRoot -Recurse -File -Filter '*.py'
if($pythonFiles.Count -lt 5){Fail 'CANDIDATE_PYTHON_FILES_INCOMPLETE'}
& $pythonCommand.Source -m py_compile @($pythonFiles.FullName)
if($LASTEXITCODE -ne 0){Fail 'PYTHON_SOURCE_SYNTAX_FAILED'}
$scriptFiles=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -File -Filter '*.ps1'
$parseErrors=@()
foreach($file in $scriptFiles){
  $tokens=$null;$errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)|Out-Null
  if($errors.Count){$parseErrors += $errors | ForEach-Object {"$($file.Name):$($_.Extent.StartLineNumber):$($_.Message)"}}
}
if($parseErrors.Count){$parseErrors;Fail 'POWERSHELL_SCRIPT_PARSE_FAILED'}
$node=Get-Command node -ErrorAction SilentlyContinue
if($node){
  & $node.Source --check (Join-Path $PackageRoot 'backend/src/palwakf_local_agents/governed_operations/static/app.js')
  if($LASTEXITCODE -ne 0){Fail 'APP_JS_SYNTAX_FAILED'}
}
$forbidden=@('"/execute"','"/dispatch"','subprocess.','requests.','httpx.','ollama','openai')
$source=Get-Content -LiteralPath (Join-Path $PackageRoot 'backend/src/palwakf_local_agents/governed_operations/router.py') -Raw -Encoding UTF8
foreach($needle in $forbidden){if($source.Contains($needle)){Fail "FORBIDDEN_RUNTIME_TOKEN=$needle"}}
'PYTHON_SOURCE_SYNTAX=PASS'
'POWERSHELL_SCRIPT_PARSE=PASS'
'APP_JS_SYNTAX=PASS'
'EXECUTION_DISPATCH_ROUTES=ABSENT'
'CANDIDATE_SYNTAX_RESULT=PASS'
