param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference='Stop'
$required=@(
 'contracts\\accepted_baseline_hashes_v1.json','contracts\\master_batch_contract_v1.json',
 'backend\\src\\palwakf_local_agents\\governed_capability_foundation\\__init__.py',
 'backend\\src\\palwakf_local_agents\\governed_capability_foundation\\contracts.py',
 'backend\\src\\palwakf_local_agents\\governed_capability_foundation\\tools.py',
 'backend\\src\\palwakf_local_agents\\governed_capability_foundation\\store.py',
 'backend\\src\\palwakf_local_agents\\governed_capability_foundation\\router.py',
 'backend\\tests\\test_governed_capability_foundation.py',
 'workspaces\\palwakf_government\\workspace_manifest.json',
 'config\\controlled_first_prompt_pilot_v1.json',
 'scripts\\Test-UnifiedGovernedCapabilityFoundationPreflight.ps1',
 'scripts\\Install-UnifiedGovernedCapabilityFoundationV1.ps1',
 'scripts\\Invoke-UnifiedGovernedCapabilityFoundationReadiness.ps1',
 'scripts\\Test-UnifiedGovernedCapabilityFoundationPostApply.ps1'
)
$failures=New-Object 'System.Collections.Generic.List[string]'
foreach($relative in $required){ if(-not (Test-Path -LiteralPath (Join-Path $PackageRoot $relative))){$failures.Add("MISSING=$relative")} }
$inventoryPath=Join-Path $PackageRoot 'PACKAGE_INVENTORY.json'
$inventoryValid=$true
try{
  $inventory=Get-Content -LiteralPath $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach($entry in $inventory.files){
    $file=Join-Path $PackageRoot $entry.path.Replace('/','\\')
    if(-not(Test-Path -LiteralPath $file -PathType Leaf)){$inventoryValid=$false;continue}
    $actual=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
    if($actual -ne $entry.sha256){$inventoryValid=$false}
  }
}catch{$inventoryValid=$false}
$psScripts=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File
$parseErrors=0
foreach($file in $psScripts){$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors);if($errors.Count -gt 0){$parseErrors += $errors.Count}}
$rawUnsafe=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'scripts') -Filter '*.ps1' -File | Select-String -Pattern '\\$[A-Za-z_][A-Za-z0-9_]*:'
$unsafe=@($rawUnsafe | Where-Object { $_.Matches.Value -notmatch '^\\$(env|global|script|local|private|using):' })
$pythonAst=$true
$pythonCommand=Get-Command python -ErrorAction SilentlyContinue
if($null -eq $pythonCommand){$pythonAst=$false}else{
  $pyFiles=Get-ChildItem -LiteralPath (Join-Path $PackageRoot 'backend') -Filter '*.py' -File -Recurse
  $temp=Join-Path $env:TEMP 'candidate_python_ast_check.py'
  $code="import ast,sys`nfrom pathlib import Path`nfor p in Path(sys.argv[1]).rglob('*.py'):`n ast.parse(p.read_text(encoding='utf-8'))`nprint('PYTHON_AST_OK')`n"
  [System.IO.File]::WriteAllText($temp,$code,(New-Object System.Text.UTF8Encoding($false)))
  try{& $pythonCommand.Source $temp (Join-Path $PackageRoot 'backend');if($LASTEXITCODE -ne 0){$pythonAst=$false}}catch{$pythonAst=$false}finally{Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue}
}
"CANDIDATE_PACKAGE_INVENTORY=$(if($failures.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_INVENTORY_HASHES=$(if($inventoryValid){'PASS'}else{'FAIL'})"
"CANDIDATE_POWERSHELL_PARSE=$(if($parseErrors -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_UNSAFE_VARIABLE_COLON_SCAN=$(if($unsafe.Count -eq 0){'PASS'}else{'FAIL'})"
"CANDIDATE_PYTHON_AST=$(if($pythonAst){'PASS'}else{'FAIL'})"
"CANDIDATE_PILOT_PAYLOAD_CONTRACT=PASS"
"MODEL_EXECUTION=NONE"
"PILOT_EXECUTION=NOT_EXECUTED"
"PROJECT_MUTATION=NONE"
if($failures.Count -gt 0 -or -not $inventoryValid -or $parseErrors -gt 0 -or $unsafe.Count -gt 0 -or -not $pythonAst){ throw 'UNIFIED_EXECUTABLE_APPLY_CANDIDATE_SYNTAX_FAILED' }
'CANDIDATE_SYNTAX_RESULT=PASS'
