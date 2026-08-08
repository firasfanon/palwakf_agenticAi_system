Set-StrictMode -Version Latest

function Get-StructuredAnalysisPayloadContractV1 {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][ValidateSet('knowledge_researcher', 'documentation_handoff')][string]$AgentId
  )

  $relativePath = switch ($AgentId) {
    'knowledge_researcher' { 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_KNOWLEDGE_RESEARCHER_V1.json' }
    'documentation_handoff' { 'task_contracts\STRUCTURED_ANALYSIS_PAYLOAD_DOCUMENTATION_HANDOFF_V1.json' }
  }

  $contractPath = Join-Path ([System.IO.Path]::GetFullPath($ProjectRoot)) $relativePath

  if (-not (Test-Path -LiteralPath $contractPath)) {
    throw "STRUCTURED_PAYLOAD_CONTRACT_NOT_FOUND=$contractPath"
  }

  return (Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Test-StructuredAnalysisPayloadExactPropertySetV1 {
  param(
    [Parameter(Mandatory = $true)][object]$Value,
    [Parameter(Mandatory = $true)][string[]]$ExpectedProperties
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
  }

  if ($Value -isnot [pscustomobject]) {
    $result.reason = 'STRUCTURED_PAYLOAD_OBJECT_REQUIRED'
    return [pscustomobject]$result
  }

  $actual = @($Value.PSObject.Properties.Name | Sort-Object)
  $expected = @($ExpectedProperties | Sort-Object)

  if ([string]::Join('|', $actual) -ne [string]::Join('|', $expected)) {
    $result.reason = 'STRUCTURED_PAYLOAD_PROPERTY_SET_INVALID'
    return [pscustomobject]$result
  }

  $result.valid = $true
  $result.reason = 'VALID'
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadTextV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][string]$FieldName,
    [Parameter(Mandatory = $true)][int]$MaxLength
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    value = ''
  }

  if ($Value -isnot [string]) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_STRING_REQUIRED"
    return [pscustomobject]$result
  }

  $text = $Value.Trim()

  if ([string]::IsNullOrWhiteSpace($text)) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_EMPTY"
    return [pscustomobject]$result
  }

  if ($text.Length -gt $MaxLength) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_TOO_LONG"
    return [pscustomobject]$result
  }

  if ($text -match '[\r\n]') {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_MULTILINE_FORBIDDEN"
    return [pscustomobject]$result
  }

  if ($text.Contains('```')) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_CODE_FENCE_FORBIDDEN"
    return [pscustomobject]$result
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.value = $text
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadStringArrayV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][string]$FieldName,
    [Parameter(Mandatory = $true)][int]$MaxCount,
    [Parameter(Mandatory = $true)][int]$MaxLength
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    values = @()
  }

  if ($null -eq $Value) {
    $items = @()
  }
  else {
    $items = @($Value)
  }

  if ($items.Count -gt $MaxCount) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_TOO_MANY_ITEMS"
    return [pscustomobject]$result
  }

  $normalized = New-Object System.Collections.Generic.List[string]

  foreach ($item in $items) {
    $textCheck = Test-StructuredAnalysisPayloadTextV1 -Value $item -FieldName $FieldName -MaxLength $MaxLength

    if (-not $textCheck.valid) {
      $result.reason = $textCheck.reason
      return [pscustomobject]$result
    }

    [void]$normalized.Add($textCheck.value)
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.values = @($normalized.ToArray())
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadEvidenceIdsV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds,
    [Parameter(Mandatory = $true)][string]$FieldName,
    [int]$MinimumCount = 1,
    [int]$MaximumCount = 4
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    values = @()
  }

  if ($null -eq $Value) {
    $items = @()
  }
  else {
    $items = @($Value)
  }

  if ($items.Count -lt $MinimumCount) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_MISSING"
    return [pscustomobject]$result
  }

  if ($items.Count -gt $MaximumCount) {
    $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_TOO_MANY"
    return [pscustomobject]$result
  }

  $normalized = New-Object System.Collections.Generic.List[string]
  $seen = @{}

  foreach ($item in $items) {
    if ($item -isnot [string]) {
      $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_STRING_REQUIRED"
      return [pscustomobject]$result
    }

    $referenceId = $item.Trim()

    if ([string]::IsNullOrWhiteSpace($referenceId)) {
      $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_EMPTY"
      return [pscustomobject]$result
    }

    if ($ExpectedEvidenceIds -notcontains $referenceId) {
      $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_UNEXPECTED_REFERENCE"
      return [pscustomobject]$result
    }

    if ($seen.ContainsKey($referenceId)) {
      $result.reason = "STRUCTURED_PAYLOAD_${FieldName}_DUPLICATE_REFERENCE"
      return [pscustomobject]$result
    }

    $seen[$referenceId] = $true
    [void]$normalized.Add($referenceId)
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.values = @($normalized.ToArray())
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadFactsV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][object]$Contract,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    values = @()
  }

  if ($null -eq $Value) {
    $items = @()
  }
  else {
    $items = @($Value)
  }

  if ($items.Count -lt [int]$Contract.limits.facts_min) {
    $result.reason = 'STRUCTURED_PAYLOAD_FACTS_MISSING'
    return [pscustomobject]$result
  }

  if ($items.Count -gt [int]$Contract.limits.facts_max) {
    $result.reason = 'STRUCTURED_PAYLOAD_FACTS_TOO_MANY'
    return [pscustomobject]$result
  }

  $normalized = New-Object System.Collections.Generic.List[object]

  foreach ($item in $items) {
    $propertyCheck = Test-StructuredAnalysisPayloadExactPropertySetV1 -Value $item -ExpectedProperties @($Contract.fact_item_keys)

    if (-not $propertyCheck.valid) {
      $result.reason = "STRUCTURED_PAYLOAD_FACT_ITEM_$($propertyCheck.reason)"
      return [pscustomobject]$result
    }

    $statementCheck = Test-StructuredAnalysisPayloadTextV1 -Value $item.statement -FieldName 'FACT_STATEMENT' -MaxLength ([int]$Contract.limits.text_max_chars)

    if (-not $statementCheck.valid) {
      $result.reason = $statementCheck.reason
      return [pscustomobject]$result
    }

    $referenceCheck = Test-StructuredAnalysisPayloadEvidenceIdsV1 `
      -Value $item.evidence_reference_ids `
      -ExpectedEvidenceIds $ExpectedEvidenceIds `
      -FieldName 'FACT_EVIDENCE_REFERENCE_IDS'

    if (-not $referenceCheck.valid) {
      $result.reason = $referenceCheck.reason
      return [pscustomobject]$result
    }

    [void]$normalized.Add([ordered]@{
      statement = $statementCheck.value
      evidence_reference_ids = $referenceCheck.values
    })
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.values = @($normalized.ToArray())
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadSourceAssessmentsV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][object]$Contract,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    values = @()
  }

  if ($null -eq $Value) {
    $items = @()
  }
  else {
    $items = @($Value)
  }

  if ($items.Count -lt [int]$Contract.limits.source_assessments_min) {
    $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENTS_MISSING'
    return [pscustomobject]$result
  }

  if ($items.Count -gt [int]$Contract.limits.source_assessments_max) {
    $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENTS_TOO_MANY'
    return [pscustomobject]$result
  }

  $normalized = New-Object System.Collections.Generic.List[object]
  $seen = @{}

  foreach ($item in $items) {
    $propertyCheck = Test-StructuredAnalysisPayloadExactPropertySetV1 -Value $item -ExpectedProperties @($Contract.source_assessment_item_keys)

    if (-not $propertyCheck.valid) {
      $result.reason = "STRUCTURED_PAYLOAD_SOURCE_ASSESSMENT_$($propertyCheck.reason)"
      return [pscustomobject]$result
    }

    if ($item.evidence_reference_id -isnot [string]) {
      $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENT_REFERENCE_STRING_REQUIRED'
      return [pscustomobject]$result
    }

    $referenceId = $item.evidence_reference_id.Trim()

    if (($ExpectedEvidenceIds -notcontains $referenceId) -or [string]::IsNullOrWhiteSpace($referenceId)) {
      $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENT_REFERENCE_UNEXPECTED'
      return [pscustomobject]$result
    }

    if ($seen.ContainsKey($referenceId)) {
      $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENT_REFERENCE_DUPLICATE'
      return [pscustomobject]$result
    }

    $assessmentCheck = Test-StructuredAnalysisPayloadTextV1 -Value $item.assessment -FieldName 'SOURCE_ASSESSMENT' -MaxLength ([int]$Contract.limits.list_item_max_chars)

    if (-not $assessmentCheck.valid) {
      $result.reason = $assessmentCheck.reason
      return [pscustomobject]$result
    }

    if ([string]$item.trust_state -ne [string]$Contract.source_assessment_trust_state) {
      $result.reason = 'STRUCTURED_PAYLOAD_SOURCE_ASSESSMENT_TRUST_STATE_INVALID'
      return [pscustomobject]$result
    }

    $seen[$referenceId] = $true
    [void]$normalized.Add([ordered]@{
      evidence_reference_id = $referenceId
      assessment = $assessmentCheck.value
      trust_state = [string]$Contract.source_assessment_trust_state
    })
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.values = @($normalized.ToArray())
  return [pscustomobject]$result
}

function Test-StructuredAnalysisPayloadHandoffSectionsV1 {
  param(
    [AllowNull()][object]$Value,
    [Parameter(Mandatory = $true)][object]$Contract,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    values = @()
  }

  if ($null -eq $Value) {
    $items = @()
  }
  else {
    $items = @($Value)
  }

  if ($items.Count -lt [int]$Contract.limits.handoff_sections_min) {
    $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_SECTIONS_MISSING'
    return [pscustomobject]$result
  }

  if ($items.Count -gt [int]$Contract.limits.handoff_sections_max) {
    $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_SECTIONS_TOO_MANY'
    return [pscustomobject]$result
  }

  $normalized = New-Object System.Collections.Generic.List[object]
  $seen = @{}

  foreach ($item in $items) {
    $propertyCheck = Test-StructuredAnalysisPayloadExactPropertySetV1 -Value $item -ExpectedProperties @($Contract.handoff_section_item_keys)

    if (-not $propertyCheck.valid) {
      $result.reason = "STRUCTURED_PAYLOAD_HANDOFF_SECTION_$($propertyCheck.reason)"
      return [pscustomobject]$result
    }

    if ($item.section -isnot [string]) {
      $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_SECTION_NAME_STRING_REQUIRED'
      return [pscustomobject]$result
    }

    $section = $item.section.Trim()

    if (@($Contract.allowed_handoff_sections) -notcontains $section) {
      $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_SECTION_NAME_INVALID'
      return [pscustomobject]$result
    }

    if ($seen.ContainsKey($section)) {
      $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_SECTION_NAME_DUPLICATE'
      return [pscustomobject]$result
    }

    $textCheck = Test-StructuredAnalysisPayloadTextV1 -Value $item.text -FieldName 'HANDOFF_SECTION_TEXT' -MaxLength ([int]$Contract.limits.text_max_chars)

    if (-not $textCheck.valid) {
      $result.reason = $textCheck.reason
      return [pscustomobject]$result
    }

    $referenceCheck = Test-StructuredAnalysisPayloadEvidenceIdsV1 `
      -Value $item.evidence_reference_ids `
      -ExpectedEvidenceIds $ExpectedEvidenceIds `
      -FieldName 'HANDOFF_SECTION_EVIDENCE_REFERENCE_IDS'

    if (-not $referenceCheck.valid) {
      $result.reason = $referenceCheck.reason
      return [pscustomobject]$result
    }

    $seen[$section] = $true
    [void]$normalized.Add([ordered]@{
      section = $section
      text = $textCheck.value
      evidence_reference_ids = $referenceCheck.values
    })
  }

  foreach ($requiredSection in @($Contract.required_handoff_sections)) {
    if (-not $seen.ContainsKey([string]$requiredSection)) {
      $result.reason = 'STRUCTURED_PAYLOAD_HANDOFF_REQUIRED_SECTION_MISSING'
      return [pscustomobject]$result
    }
  }

  $result.valid = $true
  $result.reason = 'VALID'
  $result.values = @($normalized.ToArray())
  return [pscustomobject]$result
}

function Get-CanonicalStructuredAnalysisPayloadEnvelopeV1 {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)][object]$ValidatedPayload,
    [Parameter(Mandatory = $true)][object]$Contract,
    [Parameter(Mandatory = $true)][string]$RunId,
    [Parameter(Mandatory = $true)][string]$TaskId,
    [Parameter(Mandatory = $true)][string]$AgentId,
    [Parameter(Mandatory = $true)][string]$EvidenceManifestId
  )

  $envelope = [ordered]@{
    envelope_id = "SAP-$RunId"
    envelope_version = '1.0.0'
    contract_id = [string]$Contract.contract_id
    run_id = $RunId
    task_id = $TaskId
    agent_id = $AgentId
    evidence_manifest_id = $EvidenceManifestId
    validated_at_utc = [DateTime]::UtcNow.ToString('o')
    validation_result = 'PASS'
    human_review_required = $true
    payload = $ValidatedPayload
  }

  $json = $envelope | ConvertTo-Json -Depth 20

  return @(
    'STRUCTURED_ANALYSIS_PAYLOAD_START'
    $json
    'STRUCTURED_ANALYSIS_PAYLOAD_END'
  ) -join "`n"
}

function Test-StructuredAnalysisPayloadV1 {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)][string]$RawOutput,
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][ValidateSet('knowledge_researcher', 'documentation_handoff')][string]$AgentId,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds,
    [string]$RunId = 'VALIDATION_ONLY',
    [string]$TaskId = 'VALIDATION_ONLY',
    [string]$EvidenceManifestId = 'VALIDATION_ONLY'
  )

  $result = [ordered]@{
    valid = $false
    reason = ''
    raw_utf8_bytes = 0
    normalized_payload = $null
    canonical_output = ''
  }

  $contract = Get-StructuredAnalysisPayloadContractV1 -ProjectRoot $ProjectRoot -AgentId $AgentId
  $result.raw_utf8_bytes = [System.Text.Encoding]::UTF8.GetByteCount($RawOutput)

  if ([string]::IsNullOrWhiteSpace($RawOutput)) {
    $result.reason = 'STRUCTURED_PAYLOAD_RAW_OUTPUT_EMPTY'
    return [pscustomobject]$result
  }

  if ($result.raw_utf8_bytes -gt [int]$contract.max_raw_utf8_bytes) {
    $result.reason = 'STRUCTURED_PAYLOAD_RAW_OUTPUT_TOO_LARGE'
    return [pscustomobject]$result
  }

  if ($RawOutput.TrimStart().StartsWith('```')) {
    $result.reason = 'STRUCTURED_PAYLOAD_CODE_FENCE_FORBIDDEN'
    return [pscustomobject]$result
  }

  try {
    $payload = $RawOutput | ConvertFrom-Json -ErrorAction Stop
  }
  catch {
    $result.reason = 'STRUCTURED_PAYLOAD_JSON_PARSE_FAILED'
    return [pscustomobject]$result
  }

  $propertyCheck = Test-StructuredAnalysisPayloadExactPropertySetV1 `
    -Value $payload `
    -ExpectedProperties @($contract.required_top_level_keys)

  if (-not $propertyCheck.valid) {
    $result.reason = $propertyCheck.reason
    return [pscustomobject]$result
  }

  if ([string]$payload.schema_version -ne [string]$contract.static_values.schema_version) {
    $result.reason = 'STRUCTURED_PAYLOAD_SCHEMA_VERSION_INVALID'
    return [pscustomobject]$result
  }

  if ([string]$payload.role -ne $AgentId) {
    $result.reason = 'STRUCTURED_PAYLOAD_ROLE_INVALID'
    return [pscustomobject]$result
  }

  if ([string]$payload.analysis_status -ne [string]$contract.static_values.analysis_status) {
    $result.reason = 'STRUCTURED_PAYLOAD_ANALYSIS_STATUS_INVALID'
    return [pscustomobject]$result
  }

  if ([string]$payload.recommended_next_step -ne [string]$contract.static_values.recommended_next_step) {
    $result.reason = 'STRUCTURED_PAYLOAD_NEXT_STEP_INVALID'
    return [pscustomobject]$result
  }

  $factsCheck = Test-StructuredAnalysisPayloadFactsV1 `
    -Value $payload.facts `
    -Contract $contract `
    -ExpectedEvidenceIds $ExpectedEvidenceIds

  if (-not $factsCheck.valid) {
    $result.reason = $factsCheck.reason
    return [pscustomobject]$result
  }

  $assumptionsCheck = Test-StructuredAnalysisPayloadStringArrayV1 `
    -Value $payload.assumptions `
    -FieldName 'ASSUMPTIONS' `
    -MaxCount ([int]$contract.limits.list_max) `
    -MaxLength ([int]$contract.limits.list_item_max_chars)

  if (-not $assumptionsCheck.valid) {
    $result.reason = $assumptionsCheck.reason
    return [pscustomobject]$result
  }

  $gapsCheck = Test-StructuredAnalysisPayloadStringArrayV1 `
    -Value $payload.evidence_gaps `
    -FieldName 'EVIDENCE_GAPS' `
    -MaxCount ([int]$contract.limits.list_max) `
    -MaxLength ([int]$contract.limits.list_item_max_chars)

  if (-not $gapsCheck.valid) {
    $result.reason = $gapsCheck.reason
    return [pscustomobject]$result
  }

  $risksCheck = Test-StructuredAnalysisPayloadStringArrayV1 `
    -Value $payload.risks_and_constraints `
    -FieldName 'RISKS_AND_CONSTRAINTS' `
    -MaxCount ([int]$contract.limits.list_max) `
    -MaxLength ([int]$contract.limits.list_item_max_chars)

  if (-not $risksCheck.valid) {
    $result.reason = $risksCheck.reason
    return [pscustomobject]$result
  }

  $normalized = [ordered]@{
    schema_version = [string]$contract.static_values.schema_version
    role = $AgentId
    analysis_status = [string]$contract.static_values.analysis_status
    facts = $factsCheck.values
    assumptions = $assumptionsCheck.values
    evidence_gaps = $gapsCheck.values
    risks_and_constraints = $risksCheck.values
  }

  if ($AgentId -eq 'knowledge_researcher') {
    $sourceAssessmentsCheck = Test-StructuredAnalysisPayloadSourceAssessmentsV1 `
      -Value $payload.source_assessments `
      -Contract $contract `
      -ExpectedEvidenceIds $ExpectedEvidenceIds

    if (-not $sourceAssessmentsCheck.valid) {
      $result.reason = $sourceAssessmentsCheck.reason
      return [pscustomobject]$result
    }

    $normalized.source_assessments = $sourceAssessmentsCheck.values
  }

  if ($AgentId -eq 'documentation_handoff') {
    $handoffSectionsCheck = Test-StructuredAnalysisPayloadHandoffSectionsV1 `
      -Value $payload.handoff_sections `
      -Contract $contract `
      -ExpectedEvidenceIds $ExpectedEvidenceIds

    if (-not $handoffSectionsCheck.valid) {
      $result.reason = $handoffSectionsCheck.reason
      return [pscustomobject]$result
    }

    $normalized.handoff_sections = $handoffSectionsCheck.values
  }

  $normalized.recommended_next_step = [string]$contract.static_values.recommended_next_step

  $result.valid = $true
  $result.reason = 'STRUCTURED_PAYLOAD_VALID'
  $result.normalized_payload = [pscustomobject]$normalized
  $result.canonical_output = Get-CanonicalStructuredAnalysisPayloadEnvelopeV1 `
    -ValidatedPayload $result.normalized_payload `
    -Contract $contract `
    -RunId $RunId `
    -TaskId $TaskId `
    -AgentId $AgentId `
    -EvidenceManifestId $EvidenceManifestId

  return [pscustomobject]$result
}

Export-ModuleMember -Function @(
  'Get-StructuredAnalysisPayloadContractV1',
  'Get-CanonicalStructuredAnalysisPayloadEnvelopeV1',
  'Test-StructuredAnalysisPayloadV1'
)
