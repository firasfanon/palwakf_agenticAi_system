Set-StrictMode -Version Latest

function Get-ReadOnlyEvidenceRoot {
  param([Parameter(Mandatory = $true)][string]$ProjectRoot)
  Join-Path $ProjectRoot 'reference_sources\approved'
}

function ConvertTo-SafeRelativeReferencePath {
  param([Parameter(Mandatory = $true)][string]$RelativePath)

  $normalized = $RelativePath.Replace('/', '\').TrimStart('\')

  if ([string]::IsNullOrWhiteSpace($normalized)) { throw 'REFERENCE_PATH_EMPTY' }
  if ([System.IO.Path]::IsPathRooted($normalized)) { throw 'REFERENCE_PATH_ROOTED_DENIED' }
  if ($normalized -match '(^|\\)\.\.(\\|$)') { throw 'REFERENCE_PATH_TRAVERSAL_DENIED' }

  if (-not $normalized.StartsWith('reference_sources\approved\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'REFERENCE_ROOT_DENIED'
  }

  return $normalized
}

function Get-ReferenceSecurityFlags {
  param([Parameter(Mandatory = $true)][string]$Text)

  $flags = New-Object System.Collections.Generic.List[string]
  $checks = @(
    @{
      Name = 'PROMPT_INJECTION_PATTERN_DETECTED'
      Pattern = '(?i)(ignore\s+(all|previous)|reveal\s+(secret|token|password)|bypass\s+(review|policy)|force\s+publish|deploy\s+now|run\s+sql|delete\s+(all|data|table))'
    },
    @{
      Name = 'SECRET_REQUEST_PATTERN_DETECTED'
      Pattern = '(?i)(secret|token|password|api[_ -]?key)'
    },
    @{
      Name = 'DESTRUCTIVE_REQUEST_PATTERN_DETECTED'
      Pattern = '(?i)(drop\s+table|delete\s+from|rm\s+-rf|truncate\s+table)'
    }
  )

  foreach ($check in $checks) {
    if ($Text -match $check.Pattern) { [void]$flags.Add($check.Name) }
  }

  return @($flags)
}

function New-ReferenceEvidenceManifest {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][object]$Task,
    [int]$MaxCharsPerReference = 6000
  )

  $rootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
  $approvedRoot = [System.IO.Path]::GetFullPath((Get-ReadOnlyEvidenceRoot -ProjectRoot $rootFull))
  $referencePaths = @($Task.allowed_reference_paths)

  if ($referencePaths.Count -eq 0) { throw 'NO_APPROVED_REFERENCE_PATHS' }
  if ($referencePaths.Count -gt 3) { throw 'MAX_REFERENCE_FILE_COUNT_EXCEEDED' }

  $items = @()
  $counter = 0

  foreach ($relativePath in $referencePaths) {
    $safeRelativePath = ConvertTo-SafeRelativeReferencePath -RelativePath ([string]$relativePath)
    $fullPath = [System.IO.Path]::GetFullPath((Join-Path $rootFull $safeRelativePath))

    if (-not $fullPath.StartsWith($approvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw 'REFERENCE_RESOLUTION_DENIED'
    }

    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
      throw "APPROVED_REFERENCE_NOT_FOUND=$safeRelativePath"
    }

    $item = Get-Item -LiteralPath $fullPath
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
      throw "REFERENCE_REPARSE_POINT_DENIED=$safeRelativePath"
    }
    if ($item.Length -gt 131072) { throw "REFERENCE_FILE_TOO_LARGE=$safeRelativePath" }

    $extension = [System.IO.Path]::GetExtension($fullPath).ToLowerInvariant()
    if (@('.md', '.txt', '.json', '.csv', '.yaml', '.yml') -notcontains $extension) {
      throw "REFERENCE_EXTENSION_DENIED=$safeRelativePath"
    }

    $text = Get-Content -LiteralPath $fullPath -Raw -Encoding UTF8
    $safeText = if ($text.Length -gt $MaxCharsPerReference) {
      $text.Substring(0, $MaxCharsPerReference)
    } else {
      $text
    }

    $counter++
    $evidenceId = ('EVD-{0:D3}' -f $counter)
    $snippets = @()
    $chunkSize = 1200

    for ($offset = 0; $offset -lt $safeText.Length; $offset += $chunkSize) {
      $length = [Math]::Min($chunkSize, $safeText.Length - $offset)
      $snippets += [ordered]@{
        snippet_id = ('{0}-SNIP-{1:D2}' -f $evidenceId, (($offset / $chunkSize) + 1))
        text = $safeText.Substring($offset, $length)
      }
    }

    $items += [ordered]@{
      evidence_id = $evidenceId
      relative_path = $safeRelativePath.Replace('\', '/')
      sha256 = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash
      read_at_utc = [DateTime]::UtcNow.ToString('o')
      classification = 'UNTRUSTED_REFERENCE_CONTENT'
      size_bytes = $item.Length
      snippet_ids = @($snippets | ForEach-Object { $_.snippet_id })
      snippets = $snippets
      security_flags = @(Get-ReferenceSecurityFlags -Text $safeText)
    }
  }

  $stamp = [DateTime]::UtcNow.ToString('yyyyMMddHHmmss')
  return [ordered]@{
    manifest_id = "EVM-$stamp-$($Task.task_id)"
    task_id = $Task.task_id
    created_at_utc = [DateTime]::UtcNow.ToString('o')
    tool_mode = 'READ_ONLY_EVIDENCE_GATEWAY'
    reference_root = 'reference_sources/approved'
    evidence_items = $items
    security_posture = 'UNTRUSTED_REFERENCE_CONTENT_NOT_EXECUTED'
    platform_mutation = 'NONE'
    database_access = 'NONE'
    git_write = 'NONE'
    deployment = 'NONE'
  }
}

function Get-ReadOnlyModelOutputContractV1 {
  param([Parameter(Mandatory = $true)][string]$ProjectRoot)

  $contractPath = Join-Path $ProjectRoot 'task_contracts\MODEL_OUTPUT_CONTRACT_V1.json'
  if (-not (Test-Path -LiteralPath $contractPath)) { throw "MODEL_OUTPUT_CONTRACT_NOT_FOUND=$contractPath" }

  return (Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-Sha256TextV1 {
  param([Parameter(Mandatory = $true)][string]$Text)

  $algorithm = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    return ([System.BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '')
  }
  finally {
    $algorithm.Dispose()
  }
}

function Get-CanonicalModelOutputEnvelopeV1 {
  param([Parameter(Mandatory = $true)][string]$ValidatedBody)

  $body = $ValidatedBody.Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd("`n")
  return @(
    'OUTPUT_CONTRACT_START'
    $body
    'OUTPUT_CONTRACT_END'
  ) -join "`n"
}

function Test-ReadOnlyModelOutputV1 {
  param(
    [Parameter(Mandatory = $true)][string]$RawOutput,
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$ExpectedRole,
    [Parameter(Mandatory = $true)][string[]]$ExpectedEvidenceIds
  )

  $contract = Get-ReadOnlyModelOutputContractV1 -ProjectRoot $ProjectRoot
  $normalized = $RawOutput.Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd("`n")
  $lines = @($normalized -split "`n" | ForEach-Object { $_.TrimEnd() })

  $result = [ordered]@{
    valid = $false
    reason = ''
    evidence_ids = ''
    parsed_values = [ordered]@{}
    raw_line_count = $lines.Count
    expected_raw_line_count = [int]$contract.expected_model_body_line_count
    trailing_line_count = 0
    trailing_text_sha256 = ''
    canonical_output = ''
  }

  if ($lines.Count -eq 0 -or [string]::IsNullOrWhiteSpace($lines[0])) {
    $result.reason = 'MODEL_OUTPUT_EMPTY_OR_LEADING_BLANK_LINE'
    return [PSCustomObject]$result
  }

  if ($lines.Count -ne [int]$contract.expected_model_body_line_count) {
    $result.reason = 'MODEL_OUTPUT_BODY_LINE_COUNT_INVALID'

    if ($lines.Count -gt [int]$contract.expected_model_body_line_count) {
      $extraLines = @(
        $lines |
          Select-Object -Skip ([int]$contract.expected_model_body_line_count) |
          Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
      )

      if ($extraLines.Count -gt 0) {
        $extraText = [string]::Join("`n", $extraLines)
        $result.trailing_line_count = $extraLines.Count
        $result.trailing_text_sha256 = Get-Sha256TextV1 -Text $extraText
      }
    }

    return [PSCustomObject]$result
  }

  $parsed = [ordered]@{}

  for ($index = 0; $index -lt $lines.Count; $index++) {
    $line = $lines[$index]

    if ([string]::IsNullOrWhiteSpace($line)) {
      $result.reason = 'MODEL_OUTPUT_BLANK_CONTRACT_LINE'
      return [PSCustomObject]$result
    }

    if ($line -notmatch '^[A-Z_]+=[^\r\n]*$') {
      $result.reason = 'MODEL_OUTPUT_NONCONFORMING_LINE'
      return [PSCustomObject]$result
    }

    $parts = $line.Split('=', 2)
    $key = $parts[0]
    $value = $parts[1]

    if ($key -ne $contract.required_keys[$index]) {
      $result.reason = 'MODEL_OUTPUT_KEY_ORDER_OR_NAME_INVALID'
      return [PSCustomObject]$result
    }

    if ($parsed.Contains($key)) {
      $result.reason = 'MODEL_OUTPUT_DUPLICATE_KEY'
      return [PSCustomObject]$result
    }

    $parsed[$key] = $value
  }

  foreach ($forbiddenKey in @($contract.forbidden_keys)) {
    if ($parsed.Contains($forbiddenKey)) {
      $result.reason = 'MODEL_OUTPUT_FORBIDDEN_KEY_PRESENT'
      return [PSCustomObject]$result
    }
  }

  if ($parsed['ROLE'] -ne $ExpectedRole) {
    $result.reason = 'MODEL_OUTPUT_ROLE_VALUE_INVALID'
    return [PSCustomObject]$result
  }

  foreach ($property in $contract.allowed_static_values.PSObject.Properties) {
    $key = $property.Name
    if (@($property.Value) -notcontains $parsed[$key]) {
      $result.reason = "MODEL_OUTPUT_VALUE_INVALID_$key"
      return [PSCustomObject]$result
    }
  }

  $reportedEvidenceIds = @(
    $parsed['EVIDENCE_REFERENCE_IDS'].Split(',') |
      ForEach-Object { $_.Trim() } |
      Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  )

  if ($reportedEvidenceIds.Count -eq 0) {
    $result.reason = 'MODEL_OUTPUT_EVIDENCE_IDS_EMPTY'
    return [PSCustomObject]$result
  }

  foreach ($evidenceId in $reportedEvidenceIds) {
    if ($ExpectedEvidenceIds -notcontains $evidenceId) {
      $result.reason = 'MODEL_OUTPUT_EVIDENCE_ID_UNEXPECTED'
      return [PSCustomObject]$result
    }
  }

  $result.valid = $true
  $result.reason = 'MODEL_OUTPUT_VALID'
  $result.evidence_ids = [string]::Join(',', $reportedEvidenceIds)
  $result.parsed_values = $parsed
  $result.canonical_output = Get-CanonicalModelOutputEnvelopeV1 -ValidatedBody $normalized

  return [PSCustomObject]$result
}

function Test-ReadOnlyModelOutput {
  param(
    [Parameter(Mandatory = $true)][string]$Raw,
    [Parameter(Mandatory = $true)][string]$AgentId,
    [Parameter(Mandatory = $true)][object]$Manifest
  )

  $projectRoot = Split-Path -Parent $PSScriptRoot
  $evidenceIds = @($Manifest.evidence_items | ForEach-Object { $_.evidence_id })
  $check = Test-ReadOnlyModelOutputV1 -RawOutput $Raw -ProjectRoot $projectRoot -ExpectedRole $AgentId -ExpectedEvidenceIds $evidenceIds

  return [PSCustomObject]@{
    passed = $check.valid
    reason = $check.reason
    evidence_reference_ids = @($check.evidence_ids.Split(',') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    canonical_output = $check.canonical_output
  }
}

Export-ModuleMember -Function @(
  'Get-ReadOnlyEvidenceRoot',
  'ConvertTo-SafeRelativeReferencePath',
  'Get-ReferenceSecurityFlags',
  'New-ReferenceEvidenceManifest',
  'Get-ReadOnlyModelOutputContractV1',
  'Get-Sha256TextV1',
  'Get-CanonicalModelOutputEnvelopeV1',
  'Test-ReadOnlyModelOutputV1',
  'Test-ReadOnlyModelOutput'
)
