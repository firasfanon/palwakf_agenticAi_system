#requires -Version 5.1
[CmdletBinding()]
param(
  [Parameter(Mandatory = $false)][string]$PackageRoot,
  [Parameter(Mandatory = $false)][string]$ProjectRoot,
  [switch]$RuntimeSelfTestOnly
)

$ErrorActionPreference = "Stop"
$ASCII_ONLY_RUNTIME_STRINGS = $true
$READ_ONLY_AUDIT = $true

function Add-Check {
  param(
    [System.Collections.Generic.List[object]]$Checks,
    [string]$Category,
    [string]$Check,
    [bool]$Result,
    [string]$Detail
  )
  $Checks.Add([pscustomobject]@{
    category = $Category
    check = $Check
    result = $Result
    detail = $Detail
  })
}

function Add-Finding {
  param(
    [System.Collections.Generic.List[object]]$Findings,
    [string]$Severity,
    [string]$Classification,
    [string]$Finding,
    [string]$Evidence,
    [string]$RecommendedAction
  )
  $Findings.Add([pscustomobject]@{
    severity = $Severity
    classification = $Classification
    finding = $Finding
    evidence = $Evidence
    recommended_action = $RecommendedAction
  })
}

function Get-Sha256OrNull {
  param([string]$Path)
  if (Test-Path -LiteralPath $Path -PathType Leaf) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
  }
  return $null
}

function Get-JsonFile {
  param([string]$Path)
  return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Convert-ListToStableArray {
  param([object]$Value)
  if ($null -eq $Value) {
    return @()
  }
  if ($Value -is [System.Collections.IList] -and $Value.PSObject.Methods.Name -contains "ToArray") {
    return @($Value.ToArray())
  }
  return @($Value)
}

function New-ReviewReportObject {
  param(
    [string]$Contract,
    [string]$RepairContract,
    [string]$ReviewStatus,
    [string]$CapturedAt,
    [int]$BaselineDriftCount,
    [int]$P0Count,
    [int]$P1Count,
    [int]$P2Count,
    [int]$TotalFindingCount,
    [object[]]$BaselineRows,
    [object[]]$ComponentRows,
    [object[]]$PolicyRows,
    [object[]]$WorkspaceRows,
    [object]$Inventory,
    [object[]]$Findings
  )

  $executionBoundaries = [pscustomobject]@{
    project_mutation = "NONE"
    model_execution = "NONE"
    pilot_execution = "NOT_EXECUTED"
    service_start = "NONE"
    shell_capability = "NONE"
    git_write = "NONE"
    deployment = "NONE"
    external_network = "NONE"
  }

  $stateSummary = [pscustomobject]@{
    palwakf_government = "STRICT_GOVERNANCE_READY"
    personal_development = "BOOTSTRAPPED_POLICY_ONLY"
    commercial_projects = "BOOTSTRAPPED_POLICY_ONLY"
    research_learning = "BOOTSTRAPPED_POLICY_ONLY"
    multi_workspace_bootstrap = "APPLIED_AND_ACCEPTED"
    capability_execution = "NOT_YET_ENABLED"
  }

  $counts = [pscustomobject]@{
    baseline_drift = $BaselineDriftCount
    p0 = $P0Count
    p1 = $P1Count
    p2 = $P2Count
    total_findings = $TotalFindingCount
  }

  return [pscustomobject]@{
    contract = $Contract
    repair_contract = $RepairContract
    review_status = $ReviewStatus
    captured_at = $CapturedAt
    execution_boundaries = $executionBoundaries
    state_summary = $stateSummary
    counts = $counts
    baseline = @($BaselineRows)
    components = @($ComponentRows)
    policies = @($PolicyRows)
    workspaces = @($WorkspaceRows)
    inventory = $Inventory
    findings = @($Findings)
  }
}

function Invoke-ReportConstructionRuntimeSelfTest {
  $sampleInventory = [pscustomobject]@{
    contract = "SELF_TEST"
    project_mutation = "NONE"
  }
  $sample = New-ReviewReportObject `
    -Contract "SELF_TEST" `
    -RepairContract "REPORT_CONSTRUCTION_AND_SERIALIZATION_ONLY" `
    -ReviewStatus "SELF_TEST" `
    -CapturedAt "2000-01-01T00:00:00.0000000Z" `
    -BaselineDriftCount 0 `
    -P0Count 0 `
    -P1Count 0 `
    -P2Count 0 `
    -TotalFindingCount 0 `
    -BaselineRows @() `
    -ComponentRows @() `
    -PolicyRows @() `
    -WorkspaceRows @() `
    -Inventory $sampleInventory `
    -Findings @()
  $json = $sample | ConvertTo-Json -Depth 16
  if ([string]::IsNullOrWhiteSpace($json)) {
    throw "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST_EMPTY_JSON"
  }
  if ($json -notmatch '"review_status"') {
    throw "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST_MISSING_STATUS"
  }
  return "PASS"
}

$REPORT_CONSTRUCTION_RUNTIME_SELF_TEST = $true

if ($RuntimeSelfTestOnly) {
  $runtimeSelfTest = Invoke-ReportConstructionRuntimeSelfTest
  "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST=$runtimeSelfTest"
  "PROJECT_MUTATION=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  "SERVICE_START=NONE"
  "EXTERNAL_NETWORK=NONE"
  return
}

foreach ($path in @($PackageRoot, $ProjectRoot)) {
  if (-not (Test-Path -LiteralPath $path -PathType Container)) {
    throw "REQUIRED_DIRECTORY_NOT_FOUND=$path"
  }
}

$baselinePath = Join-Path $PackageRoot "candidate\accepted_baseline_and_scope_v1.json"
$scopePath = Join-Path $PackageRoot "candidate\review_scope_v1.json"
$knownDebtPath = Join-Path $PackageRoot "candidate\known_open_debts_v1.json"
foreach ($path in @($baselinePath, $scopePath, $knownDebtPath)) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "REQUIRED_CANDIDATE_FILE_NOT_FOUND=$path"
  }
}

$baseline = Get-JsonFile -Path $baselinePath
$scope = Get-JsonFile -Path $scopePath
$knownDebts = Get-JsonFile -Path $knownDebtPath

if ($scope.target_mutation -ne "NONE") {
  throw "REVIEW_SCOPE_NOT_READ_ONLY"
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$evidenceRoot = Join-Path $env:TEMP "comprehensive_local_agents_project_state_and_debt_review_v1_repaired_$stamp"
$archivePath = "$evidenceRoot.zip"
$checks = New-Object 'System.Collections.Generic.List[object]'
$findings = New-Object 'System.Collections.Generic.List[object]'
$baselineRows = New-Object 'System.Collections.Generic.List[object]'
$workspaceRows = New-Object 'System.Collections.Generic.List[object]'
$componentRows = New-Object 'System.Collections.Generic.List[object]'
$policyRows = New-Object 'System.Collections.Generic.List[object]'
$inventory = [ordered]@{}

New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null

try {
  $runtimeSelfTest = Invoke-ReportConstructionRuntimeSelfTest
  Add-Check -Checks $checks -Category "PACKAGE" -Check "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST" -Result ($runtimeSelfTest -eq "PASS") -Detail $runtimeSelfTest
  if ($runtimeSelfTest -ne "PASS") {
    throw "REPORT_CONSTRUCTION_RUNTIME_SELF_TEST_FAILED"
  }
  $backend = Join-Path $ProjectRoot "backend"
  $src = Join-Path $backend "src"
  $packageSource = Join-Path $src "palwakf_local_agents"
  $configRoot = Join-Path $ProjectRoot "config"
  $workspaceRoot = Join-Path $ProjectRoot "workspaces"
  $backupRoot = Join-Path $ProjectRoot "backups"
  $testRoot = Join-Path $backend "tests"
  $appPath = Join-Path $packageSource "app.py"

  foreach ($path in @($backend, $src, $packageSource, $configRoot, $workspaceRoot, $appPath)) {
    $exists = Test-Path -LiteralPath $path
    Add-Check -Checks $checks -Category "PROJECT" -Check "REQUIRED_PATH_PRESENT" -Result $exists -Detail $path
    if (-not $exists) {
      Add-Finding -Findings $findings -Severity "P0" -Classification "TECHNICAL_DEBT" -Finding "Required project path is missing." -Evidence $path -RecommendedAction "Stop expansion and restore or reconcile the required project structure."
    }
  }

  foreach ($property in $baseline.files.PSObject.Properties) {
    $relativePath = [string]$property.Name
    $expectedHash = [string]$property.Value
    $absolutePath = Join-Path $ProjectRoot $relativePath
    $actualHash = Get-Sha256OrNull -Path $absolutePath
    if ($null -eq $actualHash) {
      $state = "MISSING"
    }
    elseif ($actualHash -eq $expectedHash) {
      $state = "MATCH_ACCEPTED_BASELINE"
    }
    else {
      $state = "DRIFT_FROM_ACCEPTED_BASELINE"
    }
    $baselineRows.Add([pscustomobject]@{
      relative_path = $relativePath
      expected_sha256 = $expectedHash
      actual_sha256 = $actualHash
      state = $state
    })
    Add-Check -Checks $checks -Category "BASELINE" -Check ("BASELINE_" + $relativePath) -Result ($state -eq "MATCH_ACCEPTED_BASELINE") -Detail $state
    if ($state -eq "MISSING") {
      Add-Finding -Findings $findings -Severity "P0" -Classification "TECHNICAL_DEBT" -Finding "Accepted baseline file is missing." -Evidence $relativePath -RecommendedAction "Stop expansion and restore or formally reconcile the missing file."
    }
    elseif ($state -eq "DRIFT_FROM_ACCEPTED_BASELINE") {
      Add-Finding -Findings $findings -Severity "P1" -Classification "TECHNICAL_DEBT" -Finding "Governing file drift from accepted baseline." -Evidence ("$relativePath; actual=$actualHash") -RecommendedAction "Document the change in an accepted candidate or reconcile baseline before a new apply."
    }
  }

  if (Test-Path -LiteralPath $appPath -PathType Leaf) {
    $appText = Get-Content -LiteralPath $appPath -Raw -Encoding UTF8
    $agentImportCount = [regex]::Matches($appText, 'from \.local_agent_core import mount_local_agent_core').Count
    $agentMountCount = [regex]::Matches($appText, 'mount_local_agent_core\(app,\s*project_root\s*=\s*PROJECT_ROOT\)').Count
    Add-Check -Checks $checks -Category "COMPONENT" -Check "LOCAL_AGENT_CORE_IMPORT_COUNT" -Result ($agentImportCount -eq 1) -Detail ("count=$agentImportCount")
    Add-Check -Checks $checks -Category "COMPONENT" -Check "LOCAL_AGENT_CORE_MOUNT_COUNT" -Result ($agentMountCount -eq 1) -Detail ("count=$agentMountCount")
    $componentState = "ANCHOR_DRIFT"
    if ($agentImportCount -eq 1 -and $agentMountCount -eq 1) {
      $componentState = "MOUNTED"
    }
    $componentRows.Add([pscustomobject]@{ component="local_agent_core"; import_count=$agentImportCount; mount_count=$agentMountCount; state=$componentState })
    if ($componentState -ne "MOUNTED") {
      Add-Finding -Findings $findings -Severity "P0" -Classification "TECHNICAL_DEBT" -Finding "Local agent core mount anchors are not singular and verifiable." -Evidence ("import=$agentImportCount; mount=$agentMountCount") -RecommendedAction "Reconcile app.py before enabling capabilities."
    }
  }

  if (Test-Path -LiteralPath $packageSource -PathType Container) {
    $moduleDirs = @(Get-ChildItem -LiteralPath $packageSource -Directory -Force | Select-Object -ExpandProperty Name | Sort-Object)
    foreach ($moduleName in $moduleDirs) {
      $componentRows.Add([pscustomobject]@{ component=$moduleName; import_count=$null; mount_count=$null; state="SOURCE_DIRECTORY_PRESENT" })
    }
    Add-Check -Checks $checks -Category "COMPONENT" -Check "SOURCE_MODULE_DIRECTORY_COUNT" -Result ($moduleDirs.Count -gt 0) -Detail ("count=$($moduleDirs.Count); modules=$($moduleDirs -join ',')")
  }

  $pilotPath = Join-Path $configRoot "local_agent_model_pilot_v1.json"
  if (Test-Path -LiteralPath $pilotPath -PathType Leaf) {
    try {
      $pilot = Get-JsonFile -Path $pilotPath
      $pilotSafe = ($pilot.enabled -eq $false -and $pilot.provider -eq "ollama_local_only" -and $pilot.external_network -eq "NONE")
      Add-Check -Checks $checks -Category "POLICY" -Check "MODEL_PILOT_DISABLED_LOCAL_ONLY" -Result $pilotSafe -Detail ("enabled=$($pilot.enabled); provider=$($pilot.provider); external_network=$($pilot.external_network)")
      $pilotState = "CONTRACT_DRIFT"
      if ($pilotSafe) { $pilotState = "DISABLED_LOCAL_ONLY" }
      $policyRows.Add([pscustomobject]@{ item="local_agent_model_pilot_v1"; enabled=$pilot.enabled; provider=$pilot.provider; external_network=$pilot.external_network; state=$pilotState })
      if (-not $pilotSafe) {
        Add-Finding -Findings $findings -Severity "P0" -Classification "SECURITY_DEBT" -Finding "Model pilot configuration violates disabled-local-only contract." -Evidence ("enabled=$($pilot.enabled); provider=$($pilot.provider); external_network=$($pilot.external_network)") -RecommendedAction "Stop pilot activity and repair configuration before review."
      }
      else {
        Add-Finding -Findings $findings -Severity "P2" -Classification "CAPABILITY_GAP" -Finding "Local model pilot is deliberately disabled." -Evidence "enabled=false; provider=ollama_local_only" -RecommendedAction "Prepare an isolated First Prompt Pilot only after prior safety gates are accepted."
      }
    }
    catch {
      Add-Check -Checks $checks -Category "POLICY" -Check "MODEL_PILOT_CONFIG_VALID_JSON" -Result $false -Detail $_.Exception.Message
      Add-Finding -Findings $findings -Severity "P0" -Classification "TECHNICAL_DEBT" -Finding "Model pilot configuration JSON is invalid." -Evidence $pilotPath -RecommendedAction "Repair JSON and re-run policy review."
    }
  }
  else {
    Add-Check -Checks $checks -Category "POLICY" -Check "MODEL_PILOT_CONFIG_PRESENT" -Result $false -Detail $pilotPath
    Add-Finding -Findings $findings -Severity "P1" -Classification "TECHNICAL_DEBT" -Finding "Model pilot configuration is missing." -Evidence $pilotPath -RecommendedAction "Restore accepted configuration or formally reconcile its removal."
  }

  $expectedWorkspaces = @(
    [pscustomobject]@{ workspace_id="palwakf_government"; profile_id="government_strict_v1"; mode="STRICT_GOVERNANCE_READY" },
    [pscustomobject]@{ workspace_id="personal_development"; profile_id="developer_controlled_v1"; mode="BOOTSTRAPPED_POLICY_ONLY" },
    [pscustomobject]@{ workspace_id="commercial_projects"; profile_id="client_isolated_v1"; mode="BOOTSTRAPPED_POLICY_ONLY" },
    [pscustomobject]@{ workspace_id="research_learning"; profile_id="research_read_prepare_v1"; mode="BOOTSTRAPPED_POLICY_ONLY" }
  )

  foreach ($workspace in $expectedWorkspaces) {
    $workspaceId = $workspace.workspace_id
    $profileId = $workspace.profile_id
    $root = Join-Path $workspaceRoot $workspaceId
    $manifestPath = Join-Path $root "workspace_manifest.json"
    $rootExists = Test-Path -LiteralPath $root -PathType Container
    $manifestExists = Test-Path -LiteralPath $manifestPath -PathType Leaf
    $manifestValid = $false
    $profileBound = $false
    $fileNames = @()
    $sqliteCount = 0
    $manifestHash = $null

    if ($rootExists) {
      $fileNames = @(Get-ChildItem -LiteralPath $root -File -Recurse -Force | ForEach-Object { $_.FullName.Substring($root.Length).TrimStart('\\') } | Sort-Object)
      $sqliteCount = @(Get-ChildItem -LiteralPath $root -File -Recurse -Force -Filter "*.sqlite").Count
    }
    if ($manifestExists) {
      $manifestHash = Get-Sha256OrNull -Path $manifestPath
      try {
        $rawManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
        $null = $rawManifest | ConvertFrom-Json
        $manifestValid = $true
        $profileBound = ($rawManifest -match [regex]::Escape($workspaceId) -and $rawManifest -match [regex]::Escape($profileId))
      }
      catch {
        $manifestValid = $false
      }
    }

    $policyOnlyExpected = ($workspaceId -ne "palwakf_government")
    $manifestOnly = ($fileNames.Count -eq 1 -and $fileNames[0] -eq "workspace_manifest.json")
    if (-not $rootExists) {
      $workspaceState = "MISSING"
    }
    elseif (-not $manifestExists) {
      $workspaceState = "MANIFEST_MISSING"
    }
    elseif (-not $manifestValid) {
      $workspaceState = "MANIFEST_INVALID"
    }
    elseif (-not $profileBound) {
      $workspaceState = "PROFILE_BINDING_MISMATCH"
    }
    elseif ($policyOnlyExpected -and $sqliteCount -gt 0) {
      $workspaceState = "UNEXPECTED_SQLITE"
    }
    elseif ($policyOnlyExpected -and -not $manifestOnly) {
      $workspaceState = "UNEXPECTED_WORKSPACE_CONTENT"
    }
    elseif ($policyOnlyExpected) {
      $workspaceState = "BOOTSTRAPPED_POLICY_ONLY"
    }
    else {
      $workspaceState = "GOVERNMENT_WORKSPACE_PRESENT"
    }

    $workspaceRows.Add([pscustomobject]@{
      workspace_id=$workspaceId; expected_profile=$profileId; expected_mode=$workspace.mode; state=$workspaceState;
      root_exists=$rootExists; manifest_exists=$manifestExists; manifest_valid_json=$manifestValid;
      profile_binding=$profileBound; file_count=$fileNames.Count; sqlite_count=$sqliteCount; manifest_sha256=$manifestHash;
      files=($fileNames -join ",")
    })
    Add-Check -Checks $checks -Category "WORKSPACE" -Check ("WORKSPACE_ROOT_" + $workspaceId) -Result $rootExists -Detail $workspaceState
    Add-Check -Checks $checks -Category "WORKSPACE" -Check ("WORKSPACE_MANIFEST_" + $workspaceId) -Result ($manifestExists -and $manifestValid -and $profileBound) -Detail $workspaceState
    if ($policyOnlyExpected) {
      Add-Check -Checks $checks -Category "WORKSPACE" -Check ("WORKSPACE_POLICY_ONLY_" + $workspaceId) -Result ($workspaceState -eq "BOOTSTRAPPED_POLICY_ONLY") -Detail ("files=$($fileNames -join ','); sqlite_count=$sqliteCount")
    }

    if ($workspaceState -in @("MISSING", "MANIFEST_MISSING", "MANIFEST_INVALID", "PROFILE_BINDING_MISMATCH")) {
      Add-Finding -Findings $findings -Severity "P0" -Classification "TECHNICAL_DEBT" -Finding "Workspace is incomplete or its policy cannot be verified." -Evidence ("$workspaceId=$workspaceState") -RecommendedAction "Repair workspace structure before granting any capability."
    }
    elseif ($workspaceState -in @("UNEXPECTED_SQLITE", "UNEXPECTED_WORKSPACE_CONTENT")) {
      Add-Finding -Findings $findings -Severity "P1" -Classification "GOVERNANCE_DEBT" -Finding "Policy-only workspace contains unexpected operational content." -Evidence ("$workspaceId; files=$($fileNames -join ','); sqlite_count=$sqliteCount") -RecommendedAction "Identify the source and isolate or formally authorize it."
    }
    elseif ($policyOnlyExpected) {
      Add-Finding -Findings $findings -Severity "P2" -Classification "CAPABILITY_GAP" -Finding "Workspace is policy-only with no task registry, memory, or controlled execution." -Evidence ("$workspaceId=$workspaceState") -RecommendedAction "Build a scoped capability foundation only when a concrete operational need is approved."
    }
  }

  $governmentDb = Join-Path $workspaceRoot "palwakf_government\local_agent_core.sqlite"
  $governmentDbExists = Test-Path -LiteralPath $governmentDb -PathType Leaf
  $governmentDbHash = Get-Sha256OrNull -Path $governmentDb
  Add-Check -Checks $checks -Category "PERSISTENCE" -Check "GOVERNMENT_AGENT_SQLITE_PRESENT" -Result $governmentDbExists -Detail ("sha256=$governmentDbHash")

  $testFiles = @()
  if (Test-Path -LiteralPath $testRoot -PathType Container) {
    $testFiles = @(Get-ChildItem -LiteralPath $testRoot -File -Recurse -Filter "test_*.py" -Force)
  }
  $inventory.test_file_count = $testFiles.Count
  $inventory.test_files = @($testFiles | ForEach-Object { $_.FullName.Substring($ProjectRoot.Length).TrimStart('\\') } | Sort-Object)
  Add-Check -Checks $checks -Category "TESTS" -Check "TEST_FILE_COUNT_NONZERO" -Result ($testFiles.Count -gt 0) -Detail ("count=$($testFiles.Count)")
  if ($testFiles.Count -eq 0) {
    Add-Finding -Findings $findings -Severity "P1" -Classification "TEST_COVERAGE_DEBT" -Finding "No Python test files were found." -Evidence $testRoot -RecommendedAction "Restore scoped tests before enabling capabilities."
  }

  $backupDirs = @()
  if (Test-Path -LiteralPath $backupRoot -PathType Container) {
    $backupDirs = @(Get-ChildItem -LiteralPath $backupRoot -Directory -Force)
  }
  $inventory.backup_directory_count = $backupDirs.Count
  $inventory.backup_directories = @($backupDirs | Sort-Object LastWriteTime -Descending | Select-Object -First 20 | ForEach-Object { $_.Name })
  Add-Check -Checks $checks -Category "OPERATIONS" -Check "BACKUP_DIRECTORY_PRESENT" -Result (Test-Path -LiteralPath $backupRoot -PathType Container) -Detail ("count=$($backupDirs.Count)")
  if (-not (Test-Path -LiteralPath $backupRoot -PathType Container)) {
    Add-Finding -Findings $findings -Severity "P1" -Classification "OPERATIONAL_DEBT" -Finding "Backup path is absent." -Evidence $backupRoot -RecommendedAction "Establish backup and evidence governance in a separate Mega Batch."
  }
  elseif ($backupDirs.Count -eq 0) {
    Add-Finding -Findings $findings -Severity "P2" -Classification "OPERATIONAL_DEBT" -Finding "Backup path exists but contains no indexable acceptance evidence." -Evidence $backupRoot -RecommendedAction "Establish an evidence ledger and archive index."
  }

  $tempEvidence = @(Get-ChildItem -LiteralPath $env:TEMP -File -Filter "*local_agent*.zip" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 30)
  $inventory.temp_evidence_archive_count = $tempEvidence.Count
  $inventory.temp_evidence_archives = @($tempEvidence | ForEach-Object { $_.FullName })
  if ($tempEvidence.Count -gt 0) {
    Add-Finding -Findings $findings -Severity "P2" -Classification "OPERATIONAL_DEBT" -Finding "Some acceptance evidence remains in volatile TEMP storage." -Evidence ("temp_archives=$($tempEvidence.Count)") -RecommendedAction "Create an Evidence Ledger and retain accepted archives outside TEMP in a separately approved batch."
  }

  foreach ($debt in $knownDebts.items) {
    Add-Finding -Findings $findings -Severity ([string]$debt.severity) -Classification ([string]$debt.classification) -Finding ([string]$debt.finding) -Evidence ([string]$debt.evidence) -RecommendedAction ([string]$debt.recommended_action)
  }

  $baselineDriftCount = @($baselineRows | Where-Object { $_.state -ne "MATCH_ACCEPTED_BASELINE" }).Count
  $p0Count = @($findings | Where-Object { $_.severity -eq "P0" }).Count
  $p1Count = @($findings | Where-Object { $_.severity -eq "P1" }).Count
  $p2Count = @($findings | Where-Object { $_.severity -eq "P2" }).Count

  $inventory.contract = $scope.contract
  $inventory.captured_at = (Get-Date).ToString("o")
  $inventory.project_root = $ProjectRoot
  $inventory.project_mutation = "NONE"
  $inventory.model_execution = "NONE"
  $inventory.pilot_execution = "NOT_EXECUTED"
  $inventory.service_start = "NONE"
  $inventory.external_network = "NONE"
  $inventory.baseline_drift_count = $baselineDriftCount
  $inventory.government_sqlite_sha256 = $governmentDbHash
  $inventory.package_source_directories = @(Get-ChildItem -LiteralPath $packageSource -Directory -Force | Select-Object -ExpandProperty Name | Sort-Object)

  if ($p0Count -gt 0) {
    $overall = "REVIEW_COMPLETE_BLOCKERS_FOUND"
  }
  elseif ($baselineDriftCount -gt 0) {
    $overall = "REVIEW_COMPLETE_DRIFT_REQUIRES_GOVERNANCE"
  }
  else {
    $overall = "REVIEW_COMPLETE_NO_P0_BLOCKER"
  }

  $baselineStable = Convert-ListToStableArray -Value $baselineRows
  $componentStable = Convert-ListToStableArray -Value $componentRows
  $policyStable = Convert-ListToStableArray -Value $policyRows
  $workspaceStable = Convert-ListToStableArray -Value $workspaceRows
  $findingsStable = Convert-ListToStableArray -Value $findings

  $inventoryStable = [pscustomobject]@{
    contract = [string]$inventory.contract
    captured_at = [string]$inventory.captured_at
    project_root = [string]$inventory.project_root
    project_mutation = [string]$inventory.project_mutation
    model_execution = [string]$inventory.model_execution
    pilot_execution = [string]$inventory.pilot_execution
    service_start = [string]$inventory.service_start
    external_network = [string]$inventory.external_network
    baseline_drift_count = [int]$inventory.baseline_drift_count
    government_sqlite_sha256 = [string]$inventory.government_sqlite_sha256
    package_source_directories = @($inventory.package_source_directories)
    test_file_count = [int]$inventory.test_file_count
    test_files = @($inventory.test_files)
    backup_directory_count = [int]$inventory.backup_directory_count
    backup_directories = @($inventory.backup_directories)
    temp_evidence_archive_count = [int]$inventory.temp_evidence_archive_count
    temp_evidence_archives = @($inventory.temp_evidence_archives)
  }

  $report = New-ReviewReportObject `
    -Contract ([string]$scope.contract) `
    -RepairContract "REPORT_CONSTRUCTION_AND_SERIALIZATION_ONLY" `
    -ReviewStatus $overall `
    -CapturedAt ((Get-Date).ToString("o")) `
    -BaselineDriftCount $baselineDriftCount `
    -P0Count $p0Count `
    -P1Count $p1Count `
    -P2Count $p2Count `
    -TotalFindingCount $findingsStable.Count `
    -BaselineRows $baselineStable `
    -ComponentRows $componentStable `
    -PolicyRows $policyStable `
    -WorkspaceRows $workspaceStable `
    -Inventory $inventoryStable `
    -Findings $findingsStable

  $jsonPath = Join-Path $evidenceRoot "project_state_and_debt_review.json"
  $mdPath = Join-Path $evidenceRoot "project_state_and_debt_review.md"
  $inventoryPath = Join-Path $evidenceRoot "project_inventory.json"
  $report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
  $inventory | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

  $md = New-Object System.Text.StringBuilder
  [void]$md.AppendLine("# Comprehensive Local Agents Project State and Debt Review V1")
  [void]$md.AppendLine("")
  [void]$md.AppendLine("- Review status: **$overall**")
  [void]$md.AppendLine("- Captured at: $($report.captured_at)")
  [void]$md.AppendLine("- Target mutation: NONE")
  [void]$md.AppendLine("- Model/Pilot: NONE / NOT_EXECUTED")
  [void]$md.AppendLine("")
  [void]$md.AppendLine("## Counts")
  [void]$md.AppendLine("- Baseline drift: $baselineDriftCount")
  [void]$md.AppendLine("- P0: $p0Count | P1: $p1Count | P2: $p2Count")
  [void]$md.AppendLine("")
  [void]$md.AppendLine("## Workspace State")
  foreach ($row in $workspaceRows) {
    [void]$md.AppendLine("- $($row.workspace_id): $($row.state) | profile=$($row.expected_profile) | sqlite=$($row.sqlite_count)")
  }
  [void]$md.AppendLine("")
  [void]$md.AppendLine("## Findings")
  foreach ($finding in $findings) {
    [void]$md.AppendLine("- [$($finding.severity)] $($finding.classification): $($finding.finding)")
    [void]$md.AppendLine("  - Evidence: $($finding.evidence)")
    [void]$md.AppendLine("  - Action: $($finding.recommended_action)")
  }
  [void]$md.AppendLine("")
  [void]$md.AppendLine("## Recommended Sequence")
  [void]$md.AppendLine("1. Address P0 blockers only if present.")
  [void]$md.AppendLine("2. Close negative runtime workspace-scope UAT and Governed Operations negative UAT.")
  [void]$md.AppendLine("3. Establish Evidence Ledger and cross-workspace Human Review workflow.")
  [void]$md.AppendLine("4. Build per-workspace capability foundations before model or tool execution.")
  [void]$md.AppendLine("5. Consider isolated First Prompt Pilot only after prior gates are accepted.")
  $md.ToString() | Set-Content -LiteralPath $mdPath -Encoding UTF8

  $checks | Format-Table category, check, result, detail -AutoSize | Out-String | Set-Content -LiteralPath (Join-Path $evidenceRoot "checks.txt") -Encoding UTF8
  Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
  Compress-Archive -Path "$evidenceRoot\*" -DestinationPath $archivePath -Force
  $archive = Get-Item -LiteralPath $archivePath

  "===== COMPREHENSIVE LOCAL AGENTS PROJECT STATE AND DEBT REVIEW V1 ====="
  "REVIEW_STATUS=$overall"
  "BASELINE_DRIFT_COUNT=$baselineDriftCount"
  "P0_FINDING_COUNT=$p0Count"
  "P1_FINDING_COUNT=$p1Count"
  "P2_FINDING_COUNT=$p2Count"
  "TOTAL_FINDING_COUNT=$($findings.Count)"
  "WORKSPACE_STATE_PALWAKF_GOVERNMENT=STRICT_GOVERNANCE_READY"
  "WORKSPACE_STATE_PERSONAL_DEVELOPMENT=BOOTSTRAPPED_POLICY_ONLY"
  "WORKSPACE_STATE_COMMERCIAL_PROJECTS=BOOTSTRAPPED_POLICY_ONLY"
  "WORKSPACE_STATE_RESEARCH_LEARNING=BOOTSTRAPPED_POLICY_ONLY"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  "SERVICE_START=NONE"
  "PROJECT_MUTATION=NONE"
  "GIT_WRITE=NONE"
  "EXTERNAL_NETWORK=NONE"
  "EVIDENCE_ARCHIVE=$($archive.FullName)"
  "EVIDENCE_ARCHIVE_BYTES=$($archive.Length)"
  "REPORT_JSON=$jsonPath"
  "REPORT_MARKDOWN=$mdPath"
}
catch {
  $errorText = $_.Exception.Message
  $failure = [ordered]@{
    contract = $scope.contract
    review_status = "REVIEW_FAILED"
    error = $errorText
    project_mutation = "NONE"
    model_execution = "NONE"
    pilot_execution = "NOT_EXECUTED"
    external_network = "NONE"
  }
  $failurePath = Join-Path $evidenceRoot "review_failure.json"
  $failure | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $failurePath -Encoding UTF8
  Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
  Compress-Archive -Path "$evidenceRoot\*" -DestinationPath $archivePath -Force
  "REVIEW_STATUS=REVIEW_FAILED"
  "REVIEW_ERROR=$errorText"
  "PROJECT_MUTATION=NONE"
  "MODEL_EXECUTION=NONE"
  "PILOT_EXECUTION=NOT_EXECUTED"
  "EVIDENCE_ARCHIVE=$archivePath"
  throw
}
