[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($ProjectRoot)
$registryPath = Join-Path $Root 'agents\registry\AGENT_SKILL_ASSIGNMENTS_V1.json'

if (-not (Test-Path -LiteralPath $registryPath)) {
  throw "REGISTRY_NOT_FOUND=$registryPath"
}

function Set-JsonPropertyValue {
  param(
    [Parameter(Mandatory = $true)]
    [object]$Object,

    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter(Mandatory = $true)]
    [object]$Value
  )

  $property = $Object.PSObject.Properties[$Name]

  if ($null -eq $property) {
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
  }
  else {
    $property.Value = $Value
  }
}

function Get-UniqueStringList {
  param(
    [Parameter(Mandatory = $true)]
    [object[]]$Values
  )

  $seen = @{}
  $result = New-Object System.Collections.Generic.List[string]

  foreach ($value in @($Values)) {
    $text = [string]$value

    if ([string]::IsNullOrWhiteSpace($text)) {
      continue
    }

    if (-not $seen.ContainsKey($text)) {
      $seen[$text] = $true
      [void]$result.Add($text)
    }
  }

  return @($result.ToArray())
}

$registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json

if ($null -eq $registry.agents) {
  throw 'REGISTRY_AGENTS_ARRAY_MISSING'
}

$profiles = @(
  @{
    agent_id = 'coordinator'
    profile_path = 'agents/output_profiles/read_only_analysis_pack_01/coordinator.json'
  },
  @{
    agent_id = 'sovereignty_reviewer'
    profile_path = 'agents/output_profiles/read_only_analysis_pack_01/sovereignty_reviewer.json'
  },
  @{
    agent_id = 'knowledge_researcher'
    profile_path = 'agents/output_profiles/read_only_analysis_pack_01/knowledge_researcher.json'
  },
  @{
    agent_id = 'documentation_handoff'
    profile_path = 'agents/output_profiles/read_only_analysis_pack_01/documentation_handoff.json'
  }
)

foreach ($profile in $profiles) {
  $matches = @($registry.agents | Where-Object { $_.agent_id -eq $profile.agent_id })

  if ($matches.Count -ne 1) {
    throw "REGISTRY_AGENT_COUNT_INVALID:$($profile.agent_id):$($matches.Count)"
  }
}

foreach ($profile in $profiles) {
  $agent = @($registry.agents | Where-Object { $_.agent_id -eq $profile.agent_id })[0]

  $skills = Get-UniqueStringList -Values @(
    @($agent.allowed_skills) +
    @('task_triage', 'evidence_assessment')
  )

  $autonomy = Get-UniqueStringList -Values @(
    @($agent.allowed_autonomy) +
    @('L0_READ_ONLY')
  )

  Set-JsonPropertyValue -Object $agent -Name 'runtime_enabled' -Value $true
  Set-JsonPropertyValue -Object $agent -Name 'runtime_mode' -Value 'read_only_report_only'
  Set-JsonPropertyValue -Object $agent -Name 'allowed_skills' -Value $skills
  Set-JsonPropertyValue -Object $agent -Name 'allowed_autonomy' -Value $autonomy
  Set-JsonPropertyValue -Object $agent -Name 'pack_01_profile' -Value $profile.profile_path
  Set-JsonPropertyValue -Object $agent -Name 'human_review_required' -Value $true
}

if ($PSCmdlet.ShouldProcess($registryPath, 'Enable four Pack 01 agents for L0 read-only report-only execution')) {
  $registry |
    ConvertTo-Json -Depth 30 |
    Set-Content -LiteralPath $registryPath -Encoding UTF8
}

"REGISTRY_ACTIVATION_STATUS=$(if ($WhatIfPreference) { 'WHATIF_COMPLETE' } else { 'COMPLETE' })"
"PACK_AGENT_COUNT=$($profiles.Count)"
'RUNTIME_MODE=READ_ONLY_REPORT_ONLY'
'AUTONOMY=L0_READ_ONLY'
'HUMAN_REVIEW_REQUIRED=YES'
'MODEL_EXECUTION=DISABLED_BY_DEFAULT'
'PLATFORM_MUTATION=NONE'
'DATABASE_ACCESS=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'SECRETS_ACCESS=NONE'
