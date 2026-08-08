[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$PackageRoot)
$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($PackageRoot)
if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw "PACKAGE_ROOT_NOT_FOUND=$Root" }
$files = @(Get-ChildItem -LiteralPath $Root -Recurse -File | Where-Object { $_.Extension -in @('.ps1','.psm1') } | Sort-Object FullName)
$parseFailures = @(); $unsafe = @(); $validScopes = @('env','script','global','local','private','using')
foreach ($file in $files) {
  $tokens = $null; $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
  foreach ($error in @($errors)) { $parseFailures += "$($file.FullName):$($error.Extent.StartLineNumber):$($error.Message)" }
  $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8
  foreach ($match in [regex]::Matches($text,'\$(?<name>[A-Za-z_][A-Za-z0-9_]*):')) {
    if ($validScopes -notcontains [string]$match.Groups['name'].Value) { $unsafe += "$($file.FullName):$($match.Index):$($match.Value)" }
  }
}
"PACKAGE_SCRIPT_COUNT=$($files.Count)"
"POWERSHELL_PARSE_FAILURE_COUNT=$($parseFailures.Count)"
"POWERSHELL_PARSE_FAILURES=$([string]::Join(';',$parseFailures))"
"UNSAFE_VARIABLE_COLON_INTERPOLATION_COUNT=$($unsafe.Count)"
"UNSAFE_VARIABLE_COLON_INTERPOLATIONS=$([string]::Join(';',$unsafe))"
'MODEL_EXECUTION=NONE'; 'PLATFORM_MUTATION=NONE'; 'DATABASE_ACCESS=NONE'; 'GIT_WRITE=NONE'; 'DEPLOYMENT=NONE'; 'SECRETS_ACCESS=NONE'; 'MEMORY_WRITE=NONE'
if ($parseFailures.Count -eq 0 -and $unsafe.Count -eq 0) { 'SYNTAX_GATE_RESULT=PASS'; exit 0 }
'SYNTAX_GATE_RESULT=FAIL'; exit 1
