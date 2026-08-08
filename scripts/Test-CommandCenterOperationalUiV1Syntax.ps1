[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot)
$ErrorActionPreference = "Stop"
$p=(Resolve-Path -LiteralPath $PackageRoot).Path
$required=@("static\index.html","static\styles.css","static\app.js","scripts\Test-CommandCenterOperationalUiV1Syntax.ps1","scripts\Test-CommandCenterOperationalUiV1Preflight.ps1","scripts\Test-CommandCenterOperationalUiV1StaticEval.ps1","scripts\Install-CommandCenterOperationalUiV1.ps1","docs\README_OPERATIONAL_UI_UX_READ_ONLY_V1_AR.md","docs\SECURITY_CONTRACT_OPERATIONAL_UI_UX_READ_ONLY_V1.md","docs\UAT_OPERATIONAL_UI_UX_READ_ONLY_V1_AR.md","MANIFEST_OPERATIONAL_UI_UX_READ_ONLY_V1.md")
$missing=@($required|Where-Object{-not(Test-Path -LiteralPath (Join-Path $p $_) -PathType Leaf)})
$parse=@();Get-ChildItem (Join-Path $p "scripts") -Filter "*.ps1" -File|ForEach-Object{$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e);$e|ForEach-Object{$parse+="$($_.Extent.StartLineNumber):$($_.Message)"}}
$js=Get-Content (Join-Path $p "static\app.js") -Raw -Encoding UTF8;$html=Get-Content (Join-Path $p "static\index.html") -Raw -Encoding UTF8
$markers=@();foreach($needle in @('lang="ar" dir="rtl"','لا تشغيل · لا نشر · لا كتابة','/system-health','/governance')){if(($html+$js)-notmatch [regex]::Escape($needle)){$markers+=$needle}}
$forbid=@();if($js -match '(?i)\bmethod\s*:\s*[''"](?:POST|PUT|PATCH|DELETE)[''"]'){$forbid+='NON_GET_METHOD'};if($js -match '(?i)\b(localStorage|sessionStorage)\.(setItem|removeItem|clear)\s*\('){$forbid+='BROWSER_STORAGE_WRITE'}
"REQUIRED_FILE_COUNT=$($required.Count)";"MISSING_FILE_COUNT=$($missing.Count)";"POWERSHELL_PARSE_FAILURE_COUNT=$($parse.Count)";"UI_MARKER_FAILURE_COUNT=$($markers.Count)";"FORBIDDEN_UI_PATTERN_COUNT=$($forbid.Count)";"UI_SCOPE=STATIC_ASSETS_ONLY";"UI_LANGUAGE=ARABIC_RTL";"UI_MODE=READ_ONLY_OPERATIONAL_DASHBOARD";"MODEL_EXECUTION=NONE";"PILOT_EXECUTION=NOT_EXECUTED"
if($missing.Count -or $parse.Count -or $markers.Count -or $forbid.Count){"SYNTAX_GATE_RESULT=FAIL";exit 1};"SYNTAX_GATE_RESULT=PASS"