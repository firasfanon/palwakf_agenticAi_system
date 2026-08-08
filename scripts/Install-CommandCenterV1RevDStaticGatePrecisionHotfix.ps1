[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PackageRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ProjectRoot,

    [ValidateSet("Upgrade")]
    [string]$Mode = "Upgrade"
)

$ErrorActionPreference = "Stop"
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path

$sourceGate = Join-Path $package "scripts\Test-CommandCenterV1RevBStatic.ps1"
$targetGate = Join-Path $project "scripts\Test-CommandCenterV1RevBStatic.ps1"

foreach ($path in @($sourceGate, $targetGate)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "REQUIRED_FILE_NOT_FOUND=$path"
    }
}

$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$backupRoot = Join-Path $project "backups\command_center_v1_2_revd_static_gate_$timestamp"
$preimagePath = Join-Path $backupRoot "preimage\scripts\Test-CommandCenterV1RevBStatic.ps1"
$manifestPath = Join-Path $backupRoot "install_preimage_manifest.json"

if ($WhatIfPreference) {
    if ($PSCmdlet.ShouldProcess($backupRoot, "Create Command Center Rev D static-gate preimage backup")) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $preimagePath) -Force | Out-Null
    }
    if ($PSCmdlet.ShouldProcess($preimagePath, "Backup existing Command Center static gate")) {
        Copy-Item -LiteralPath $targetGate -Destination $preimagePath -Force
    }
    if ($PSCmdlet.ShouldProcess($manifestPath, "Write Command Center Rev D static-gate preimage manifest")) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $manifestPath) -Force | Out-Null
    }
    if ($PSCmdlet.ShouldProcess($targetGate, "Install precision static gate with generic replace excluded")) {
        Copy-Item -LiteralPath $sourceGate -Destination $targetGate -Force
    }

    Write-Output "INSTALL_STATUS=WHATIF_COMPLETE"
    Write-Output "INSTALL_MODE=$Mode"
    Write-Output "BACKUP_PATH=$backupRoot"
    Write-Output "BACKUP_MANIFEST_PATH=$manifestPath"
    Write-Output "BACKUP_STATUS=PLANNED"
    Write-Output "INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY"
    Write-Output "GENERIC_STRING_REPLACE_TREATMENT=NON_MUTATING_EXCLUDED"
    Write-Output "FILE_MUTATION_SCAN_SCOPE=PYTHON_FILESYSTEM_OPERATIONS_ONLY"
    Write-Output "WEB_NON_GET_METHOD_SCAN=PLANNED"
    Write-Output "APP_ENTRYPOINT_MUTATION=NONE"
    Write-Output "COMMAND_CENTER_RUNTIME_MUTATION=NONE"
    Write-Output "LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED"
    Write-Output "PROJECT_MUTATION=NONE"
    exit 0
}

New-Item -ItemType Directory -Path (Split-Path -Parent $preimagePath) -Force | Out-Null
Copy-Item -LiteralPath $targetGate -Destination $preimagePath -Force

$sourceHash = (Get-FileHash -LiteralPath $sourceGate -Algorithm SHA256).Hash
$preimageHash = (Get-FileHash -LiteralPath $targetGate -Algorithm SHA256).Hash

$manifest = [ordered]@{
    package_id = "PALWAKF_LOCAL_AGENTS_COMMAND_CENTER_V1_2_REVD_STATIC_GATE_PRECISION_HOTFIX"
    created_at_local = (Get-Date).ToString("o")
    install_mode = $Mode
    target_static_gate = "scripts/Test-CommandCenterV1RevBStatic.ps1"
    source_static_gate_sha256 = $sourceHash
    preimage_static_gate_sha256 = $preimageHash
    patch_scope = "STATIC_GATE_GENERIC_STRING_REPLACE_PRECISION_ONLY"
    app_entrypoint_mutation = "NONE"
    command_center_runtime_mutation = "NONE"
    core_runtime_mutation = "NONE"
    model_execution = "NONE"
    pilot_execution = "NOT_EXECUTED"
}

New-Item -ItemType Directory -Path (Split-Path -Parent $manifestPath) -Force | Out-Null
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Copy-Item -LiteralPath $sourceGate -Destination $targetGate -Force

$installedHash = (Get-FileHash -LiteralPath $targetGate -Algorithm SHA256).Hash
if ($installedHash -ne $sourceHash) {
    throw "STATIC_GATE_INSTALL_HASH_MISMATCH"
}

Write-Output "INSTALL_STATUS=COMPLETE"
Write-Output "INSTALL_MODE=$Mode"
Write-Output "BACKUP_PATH=$backupRoot"
Write-Output "BACKUP_MANIFEST_PATH=$manifestPath"
Write-Output "BACKUP_STATUS=COMPLETE"
Write-Output "INSTALL_BACKUP_STRATEGY=EXACT_FILE_PREIMAGE_COPY"
Write-Output "SOURCE_STATIC_GATE_SHA256=$sourceHash"
Write-Output "INSTALLED_STATIC_GATE_SHA256=$installedHash"
Write-Output "GENERIC_STRING_REPLACE_TREATMENT=NON_MUTATING_EXCLUDED"
Write-Output "FILE_MUTATION_SCAN_SCOPE=PYTHON_FILESYSTEM_OPERATIONS_ONLY"
Write-Output "WEB_NON_GET_METHOD_SCAN=ACTIVE"
Write-Output "APP_ENTRYPOINT_MUTATION=NONE"
Write-Output "COMMAND_CENTER_RUNTIME_MUTATION=NONE"
Write-Output "LEGACY_ROOT_COMMAND_CENTER_ACTION=UNCHANGED"
Write-Output "CORE_RUNTIME_MUTATION=NONE"
Write-Output "CORE_11_LINE_CONTRACT_MUTATION=NONE"
Write-Output "MODEL_EXECUTION=NONE"
Write-Output "PILOT_EXECUTION=NOT_EXECUTED"
Write-Output "PLATFORM_MUTATION=NONE"
Write-Output "DATABASE_ACCESS=NONE"
Write-Output "GIT_WRITE=NONE"
Write-Output "DEPLOYMENT=NONE"
Write-Output "SECRETS_ACCESS=NONE"
Write-Output "MEMORY_WRITE=NONE"
Write-Output "NEXT_STEP=RUN_STATIC_GATE_EVAL_AND_EXISTING_RUNTIME_VERIFICATION"
exit 0
