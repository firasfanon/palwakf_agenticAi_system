[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PackageRoot
)

$ErrorActionPreference = "Stop"
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$gate = Join-Path $package "scripts\Test-CommandCenterV1RevBStatic.ps1"

if (-not (Test-Path -LiteralPath $gate -PathType Leaf)) {
    throw "EVAL_GATE_NOT_FOUND=$gate"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("command_center_revd_eval_" + [guid]::NewGuid().ToString("N"))
$sourceRoot = Join-Path $tempRoot "backend\src\palwakf_local_agents\command_center"
$staticRoot = Join-Path $sourceRoot "static"
$testRoot = Join-Path $tempRoot "backend\tests"
$scriptsRoot = Join-Path $tempRoot "scripts"

try {
    New-Item -ItemType Directory -Path $staticRoot, $testRoot, $scriptsRoot -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $tempRoot "backend\src\palwakf_local_agents") -Force | Out-Null

    @'
from .command_center import mount_command_center
PROJECT_ROOT = "x"
mount_command_center(app, project_root=PROJECT_ROOT)
'@ | Set-Content -LiteralPath (Join-Path $tempRoot "backend\src\palwakf_local_agents\app.py") -Encoding UTF8

    "" | Set-Content -LiteralPath (Join-Path $sourceRoot "__init__.py") -Encoding UTF8
    "" | Set-Content -LiteralPath (Join-Path $sourceRoot "models.py") -Encoding UTF8
    @'
value = "relative/path".replace("\\", "/")
'@ | Set-Content -LiteralPath (Join-Path $sourceRoot "read_only_store.py") -Encoding UTF8
    @'
from fastapi import APIRouter
api = APIRouter()
@api.get("/dashboard")
def dashboard():
    return {}
'@ | Set-Content -LiteralPath (Join-Path $sourceRoot "router.py") -Encoding UTF8
    '<!doctype html>' | Set-Content -LiteralPath (Join-Path $staticRoot "index.html") -Encoding UTF8
    'body{}' | Set-Content -LiteralPath (Join-Path $staticRoot "styles.css") -Encoding UTF8
    'const label = "A_B".replace("_", " ");' | Set-Content -LiteralPath (Join-Path $staticRoot "app.js") -Encoding UTF8
    "" | Set-Content -LiteralPath (Join-Path $testRoot "test_command_center_read_only.py") -Encoding UTF8

    $passOutput = @(& $gate -ProjectRoot $tempRoot)
    $passText = [string]::Join("`n", @($passOutput | ForEach-Object { "$_" }))
    if ($passText -notmatch "FINAL_RESULT=PASS") {
        throw "EVAL_STRING_REPLACE_FALSE_POSITIVE_NOT_CLOSED"
    }

    @'
from pathlib import Path
Path("unsafe.txt").write_text("x")
'@ | Set-Content -LiteralPath (Join-Path $sourceRoot "read_only_store.py") -Encoding UTF8

    $failOutput = @(& $gate -ProjectRoot $tempRoot)
    $failText = [string]::Join("`n", @($failOutput | ForEach-Object { "$_" }))
    if ($failText -notmatch "FINAL_RESULT=FAIL") {
        throw "EVAL_FILESYSTEM_WRITE_NEGATIVE_NOT_REJECTED"
    }
    if ($failText -notmatch "PATH_WRITE_TEXT") {
        throw "EVAL_FILESYSTEM_WRITE_MARKER_MISSING"
    }

    @'
const data = {};
fetch("/api/v1/local-agents/dashboard", { method: "POST" });
'@ | Set-Content -LiteralPath (Join-Path $staticRoot "app.js") -Encoding UTF8

    # Restore read-only Python source so only the web non-GET method causes the failure.
    @'
value = "relative/path".replace("\\", "/")
'@ | Set-Content -LiteralPath (Join-Path $sourceRoot "read_only_store.py") -Encoding UTF8

    $webFailOutput = @(& $gate -ProjectRoot $tempRoot)
    $webFailText = [string]::Join("`n", @($webFailOutput | ForEach-Object { "$_" }))
    if ($webFailText -notmatch "FINAL_RESULT=FAIL") {
        throw "EVAL_WEB_NON_GET_NEGATIVE_NOT_REJECTED"
    }
    if ($webFailText -notmatch "WEB_NON_GET_METHOD") {
        throw "EVAL_WEB_NON_GET_MARKER_MISSING"
    }

    Write-Output "EVAL_CASE=STRING_REPLACE_FALSE_POSITIVE_REJECTED"
    Write-Output "EVAL_CASE=PYTHON_FILESYSTEM_WRITE_NEGATIVE_REJECTED"
    Write-Output "EVAL_CASE=WEB_NON_GET_METHOD_NEGATIVE_REJECTED"
    Write-Output "EVAL_CASE_COUNT=3"
    Write-Output "EVAL_PASSED_COUNT=3"
    Write-Output "EVAL_FAILED_COUNT=0"
    Write-Output "EVAL_RESULT=PASS"
    exit 0
}
finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
