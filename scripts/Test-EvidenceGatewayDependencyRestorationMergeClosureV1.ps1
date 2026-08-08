[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)

$modulePath = Join-Path $Root 'runtime\ReadOnlyRuntimeContextEvidenceV1.psm1'
$gatewayPath = Join-Path $Root 'scripts\Invoke-ReadOnlyEvidenceGatewayV1.ps1'
$referencePath = 'reference_sources\approved\PILOT_READ_ONLY_REFERENCE_V1.md'

$requiredFunctions = @(
  'Get-ReadOnlyEvidenceRoot',
  'ConvertTo-SafeRelativeReferencePath',
  'Get-ReferenceSecurityFlags',
  'New-ReferenceEvidenceManifest',
  'Get-ReadOnlyModelOutputContractV1',
  'Get-Sha256TextV1',
  'Test-ReadOnlyModelOutputV1',
  'Test-ReadOnlyModelOutput'
)

$missingItems = @()

foreach ($path in @($modulePath, $gatewayPath, (Join-Path $Root $referencePath))) {
  if (-not (Test-Path -LiteralPath $path)) {
    $missingItems += $path
  }
}

$moduleCommands = @()
$missingFunctions = @()
$gatewayImportPresent = $false
$gatewayManifestCallPresent = $false
$manifestProbePass = $false
$manifestEvidenceItemCount = 0
$manifestProbeReason = 'NOT_RUN'

if ($missingItems.Count -eq 0) {
  $moduleInfo = Import-Module $modulePath -Force -PassThru
  $moduleCommands = @(Get-Command -Module $moduleInfo.Name)
  $commandNames = @($moduleCommands | ForEach-Object { $_.Name })

  foreach ($name in $requiredFunctions) {
    if ($commandNames -notcontains $name) {
      $missingFunctions += $name
    }
  }

  $gatewayText = Get-Content -LiteralPath $gatewayPath -Raw -Encoding UTF8
  $gatewayImportPresent = $gatewayText.Contains('ReadOnlyRuntimeContextEvidenceV1.psm1')
  $gatewayManifestCallPresent = $gatewayText.Contains('New-ReferenceEvidenceManifest')

  if ($missingFunctions.Count -eq 0) {
    try {
      $probeTask = [PSCustomObject]@{
        task_id = 'DEPENDENCY_RESTORATION_STATIC_PROBE'
        allowed_reference_paths = @(
          'reference_sources/approved/PILOT_READ_ONLY_REFERENCE_V1.md'
        )
      }

      $probe = New-ReferenceEvidenceManifest `
        -ProjectRoot $Root `
        -Task $probeTask `
        -MaxCharsPerReference 6000

      $manifestEvidenceItemCount = @($probe.evidence_items).Count

      $manifestProbePass = (
        $probe.tool_mode -eq 'READ_ONLY_EVIDENCE_GATEWAY' -and
        $probe.platform_mutation -eq 'NONE' -and
        $probe.database_access -eq 'NONE' -and
        $probe.git_write -eq 'NONE' -and
        $probe.deployment -eq 'NONE' -and
        $manifestEvidenceItemCount -eq 1 -and
        $probe.evidence_items[0].classification -eq 'UNTRUSTED_REFERENCE_CONTENT'
      )

      $manifestProbeReason = if ($manifestProbePass) {
        'MANIFEST_PROBE_ACCEPTED'
      }
      else {
        'MANIFEST_PROBE_CONTRACT_INVALID'
      }
    }
    catch {
      $manifestProbeReason = $_.Exception.Message
    }
  }
}

"REQUIRED_FUNCTION_COUNT=$($requiredFunctions.Count)"
"MISSING_ITEM_COUNT=$($missingItems.Count)"
"MISSING_FUNCTION_COUNT=$($missingFunctions.Count)"
"MISSING_FUNCTIONS=$([string]::Join(',', $missingFunctions))"
"GATEWAY_IMPORT_PRESENT=$gatewayImportPresent"
"GATEWAY_MANIFEST_CALL_PRESENT=$gatewayManifestCallPresent"
"MANIFEST_PROBE_EVIDENCE_ITEM_COUNT=$manifestEvidenceItemCount"
"MANIFEST_PROBE=$manifestProbeReason"
'MODEL_EXECUTION=NONE'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'

if (
  $missingItems.Count -eq 0 -and
  $missingFunctions.Count -eq 0 -and
  $gatewayImportPresent -and
  $gatewayManifestCallPresent -and
  $manifestProbePass
) {
  'FINAL_RESULT=PASS'
  exit 0
}

'FINAL_RESULT=FAIL'
exit 1
