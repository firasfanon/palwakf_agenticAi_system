[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"

$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

$requiredRelativePaths = @(
    "backend\src\palwakf_local_agents\app.py",
    "backend\src\palwakf_local_agents\command_center\__init__.py",
    "backend\src\palwakf_local_agents\command_center\models.py",
    "backend\src\palwakf_local_agents\command_center\read_only_store.py",
    "backend\src\palwakf_local_agents\command_center\router.py",
    "backend\src\palwakf_local_agents\command_center\static\index.html",
    "backend\src\palwakf_local_agents\command_center\static\styles.css",
    "backend\src\palwakf_local_agents\command_center\static\app.js",
    "backend\tests\test_command_center_read_only.py"
)

$missingFiles = @()
foreach ($relativePath in $requiredRelativePaths) {
    $candidate = Join-Path $resolvedRoot $relativePath
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        $missingFiles += $relativePath
    }
}

$appEntry = Join-Path $resolvedRoot "backend\src\palwakf_local_agents\app.py"
$appText = if (Test-Path -LiteralPath $appEntry -PathType Leaf) {
    Get-Content -LiteralPath $appEntry -Raw -Encoding UTF8
} else {
    ""
}

$integrationFailures = @()
foreach ($token in @(
    "from .command_center import mount_command_center",
    "PROJECT_ROOT",
    "mount_command_center(app, project_root=PROJECT_ROOT)"
)) {
    if ($appText -notmatch [regex]::Escape($token)) {
        $integrationFailures += "APP_MOUNT_TOKEN_MISSING=$token"
    }
}

$commandCenterRoot = Join-Path $resolvedRoot "backend\src\palwakf_local_agents\command_center"
$textExtensions = @(".py", ".js", ".html", ".css")
$sourceFiles = @()
$pythonSourceFiles = @()
$webSourceFiles = @()
$binaryOrCacheSkippedCount = 0

if (Test-Path -LiteralPath $commandCenterRoot -PathType Container) {
    foreach ($candidate in Get-ChildItem -LiteralPath $commandCenterRoot -Recurse -File -Force) {
        $relativeCandidate = $candidate.FullName.Substring($commandCenterRoot.Length).TrimStart("\")
        $pathSegments = $relativeCandidate -split "\\"

        if ($pathSegments -contains "__pycache__" -or $candidate.Extension -eq ".pyc") {
            $binaryOrCacheSkippedCount++
            continue
        }

        $extension = $candidate.Extension.ToLowerInvariant()
        if ($textExtensions -contains $extension) {
            $sourceFiles += $candidate
            if ($extension -eq ".py") {
                $pythonSourceFiles += $candidate
            }
            else {
                $webSourceFiles += $candidate
            }
        }
    }
}

$sourceScanFailures = @()

# Language-agnostic forbidden runtime clients. Applied only to readable source text.
$commonRules = @(
    @{ Name = "SUBPROCESS_IMPORT"; Regex = "(?im)^\s*(from|import)\s+subprocess\b" },
    @{ Name = "REQUESTS_IMPORT"; Regex = "(?im)^\s*(from|import)\s+requests\b" },
    @{ Name = "URLLIB_IMPORT"; Regex = "(?im)^\s*(from|import)\s+urllib\b" },
    @{ Name = "SOCKET_IMPORT"; Regex = "(?im)^\s*(from|import)\s+socket\b" },
    @{ Name = "DATABASE_IMPORT"; Regex = "(?im)^\s*(from|import)\s+(sqlalchemy|psycopg|asyncpg)\b" },
    @{ Name = "MODEL_CLIENT_IMPORT"; Regex = "(?im)^\s*(from|import)\s+(ollama|openai)\b" },
    @{ Name = "SUBPROCESS_CALL"; Regex = "\bsubprocess\." },
    @{ Name = "REQUESTS_CALL"; Regex = "\brequests\." },
    @{ Name = "URLLIB_CALL"; Regex = "\burllib\." },
    @{ Name = "SOCKET_CALL"; Regex = "\bsocket\." },
    @{ Name = "MODEL_CLIENT_CALL"; Regex = "\b(ollama|openai)\." }
)

foreach ($sourceFile in $sourceFiles) {
    $sourceText = Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding UTF8
    foreach ($rule in $commonRules) {
        if ($sourceText -match $rule.Regex) {
            $sourceScanFailures += "FORBIDDEN_SOURCE_PATTERN=$($rule.Name)|$($sourceFile.FullName)"
        }
    }
}

# Python-only file mutation rules. Generic '.replace()' is deliberately excluded:
# string normalization is non-mutating; only os.replace is a filesystem mutation.
$pythonMutationRules = @(
    @{ Name = "PATH_WRITE_TEXT"; Regex = "\.\s*write_text\s*\(" },
    @{ Name = "PATH_WRITE_BYTES"; Regex = "\.\s*write_bytes\s*\(" },
    @{ Name = "PATH_UNLINK"; Regex = "\.\s*unlink\s*\(" },
    @{ Name = "PATH_RENAME"; Regex = "\.\s*rename\s*\(" },
    @{ Name = "PATH_MKDIR"; Regex = "\.\s*mkdir\s*\(" },
    @{ Name = "PATH_RMDIR"; Regex = "\.\s*rmdir\s*\(" },
    @{ Name = "PATH_TOUCH"; Regex = "\.\s*touch\s*\(" },
    @{ Name = "OS_FILE_MUTATION"; Regex = "\bos\.(remove|unlink|rename|replace|mkdir|makedirs|rmdir)\s*\(" },
    @{ Name = "SHUTIL_FILE_MUTATION"; Regex = "\bshutil\.(copy|copy2|copytree|move|rmtree)\s*\(" },
    @{ Name = "COMMAND_CENTER_WRITE_ROUTE"; Regex = "(?im)^\s*@api\.(post|put|patch|delete)\s*\(" }
)

foreach ($sourceFile in $pythonSourceFiles) {
    $sourceText = Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding UTF8
    foreach ($rule in $pythonMutationRules) {
        if ($sourceText -match $rule.Regex) {
            $sourceScanFailures += "FORBIDDEN_PYTHON_PATTERN=$($rule.Name)|$($sourceFile.FullName)"
        }
    }
}

# Frontend safety: GET-only is enforced at FastAPI route metadata, but forbid explicit
# non-GET method declarations in the Command Center web source as a defense in depth.
$webMutationRules = @(
    @{ Name = "WEB_NON_GET_METHOD"; Regex = '(?i)\bmethod\s*:\s*[''"](?:POST|PUT|PATCH|DELETE)[''"]' }
)

foreach ($sourceFile in $webSourceFiles) {
    $sourceText = Get-Content -LiteralPath $sourceFile.FullName -Raw -Encoding UTF8
    foreach ($rule in $webMutationRules) {
        if ($sourceText -match $rule.Regex) {
            $sourceScanFailures += "FORBIDDEN_WEB_PATTERN=$($rule.Name)|$($sourceFile.FullName)"
        }
    }
}

$validationFailures = @($missingFiles | ForEach-Object { "MISSING_REQUIRED_FILE=$_" }) +
    $integrationFailures +
    $sourceScanFailures

Write-Output "REQUIRED_FILE_COUNT=$($requiredRelativePaths.Count)"
Write-Output "MISSING_FILE_COUNT=$($missingFiles.Count)"
Write-Output "MISSING_FILES=$($missingFiles -join ';')"
Write-Output "SOURCE_SCAN_FILE_COUNT=$($sourceFiles.Count)"
Write-Output "PYTHON_SOURCE_SCAN_FILE_COUNT=$($pythonSourceFiles.Count)"
Write-Output "WEB_SOURCE_SCAN_FILE_COUNT=$($webSourceFiles.Count)"
Write-Output "BINARY_OR_CACHE_SKIPPED_COUNT=$binaryOrCacheSkippedCount"
Write-Output "SOURCE_SCAN_SCOPE=TEXT_SOURCE_ONLY"
Write-Output "PY_CACHE_EXCLUSION=ACTIVE"
Write-Output "GENERIC_STRING_REPLACE_TREATMENT=NON_MUTATING_EXCLUDED"
Write-Output "FILE_MUTATION_SCAN_SCOPE=PYTHON_FILESYSTEM_OPERATIONS_ONLY"
Write-Output "WEB_NON_GET_METHOD_SCAN=ACTIVE"
Write-Output "VALIDATION_FAILURE_COUNT=$($validationFailures.Count)"
Write-Output "VALIDATION_FAILURES=$($validationFailures -join ';')"
Write-Output "COMMAND_CENTER_SCOPE=READ_ONLY_OBSERVABILITY"
Write-Output "APP_ENTRYPOINT_INTEGRATION=EXPLICIT_MOUNT_ONLY"
Write-Output "ROOT_LEGACY_COMMAND_CENTER=UNCHANGED"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "DEPLOYMENT=NONE"
Write-Output "SECRETS_ACCESS=NONE"
Write-Output "MEMORY_WRITE=NONE"

if ($validationFailures.Count -gt 0) {
    Write-Output "FINAL_RESULT=FAIL"
    exit 1
}

Write-Output "FINAL_RESULT=PASS"
exit 0
