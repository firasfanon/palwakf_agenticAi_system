param(
  [Parameter(Mandatory=$true)][string]$WorkspaceRepo,
  [Parameter(Mandatory=$true)][string]$AgenticRepo,
  [Parameter(Mandatory=$true)][string]$WorkspaceExpectedHead,
  [Parameter(Mandatory=$true)][string]$AgenticExpectedHead,
  [string]$MachinePythonExe = "C:\Program Files\Python311\python.exe",
  [string]$AuthorityKeyId = "workspace-c7r-pre-gate-a-v1"
)

$ErrorActionPreference = 'Stop'
$WorkspaceBranch = 'task/WORKSPACE-C7R-PRE-GATE-A-AUTHORITY-ISSUER-V1'
$AgenticBranch = 'task/AGENTIC-C7R-PRE-GATE-A-PHASE-A-CAPABILITY-V1'
$Repository = 'firasfanon/palwakf_agenticAi_system'
$ExecutorId = 'DESKTOP-S5A0JSB'
$ServiceName = 'PalWakfOutboundLocalExecutorV1'
$BootstrapRoot = 'C:\ProgramData\PalWakf\c7r_pre_gate_a_bootstrap_v1'
$WorkspaceWorktree = Join-Path $BootstrapRoot 'workspace'
$AgenticWorktree = Join-Path $BootstrapRoot 'agentic'
$AuthorityRoot = 'C:\ProgramData\PalWakf\workspace_authority_v1'
$AuthorityKeyPath = Join-Path $AuthorityRoot 'secrets\workspace-ed25519.dpapi'
$TrustStorePath = 'C:\ProgramData\PalWakf\outbound_executor_v1\authority-keys.json'
$C7RRoot = 'C:\ProgramData\PalWakf\c7r_phase_a_v1'
$RuntimeMarkerPath = Join-Path $C7RRoot 'runtime-admission.json'
$NewLine = [Environment]::NewLine
$Fence = ([string][char]96) * 3

function Assert-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "REQUIRED_COMMAND_NOT_FOUND:$Name"
  }
}

function Invoke-Git([string]$Repo, [string[]]$Args) {
  $output = @(& git -C $Repo @Args 2>&1)
  if ($LASTEXITCODE -ne 0) {
    throw "GIT_FAILED:$($Args -join ' '):$($output -join ' ')"
  }
  return ($output -join $NewLine).Trim()
}

function Get-RemoteHead([string]$Repo, [string]$Branch) {
  $line = Invoke-Git $Repo @('ls-remote','--heads','origin',"refs/heads/$Branch")
  if (-not $line) { throw "REMOTE_BRANCH_NOT_FOUND:$Branch" }
  return ($line -split '\s+')[0].ToLowerInvariant()
}

function New-DetachedWorktree(
  [string]$Repo,
  [string]$Branch,
  [string]$ExpectedHead,
  [string]$Path
) {
  Invoke-Git $Repo @('fetch','--no-tags','origin',"refs/heads/$Branch") | Out-Null
  $remote = Get-RemoteHead $Repo $Branch
  if ($remote -ne $ExpectedHead.ToLowerInvariant()) {
    throw "REMOTE_HEAD_DRIFT:${Branch}:EXPECTED=${ExpectedHead}:ACTUAL=${remote}"
  }
  Invoke-Git $Repo @('cat-file','-e',"$ExpectedHead^{commit}") | Out-Null
  if (Test-Path -LiteralPath $Path) {
    try { Invoke-Git $Repo @('worktree','remove','--force',$Path) | Out-Null } catch {}
    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
  }
  Invoke-Git $Repo @('worktree','prune') | Out-Null
  Invoke-Git $Repo @('worktree','add','--detach',$Path,$ExpectedHead) | Out-Null
  $actual = Invoke-Git $Path @('rev-parse','HEAD')
  if ($actual.ToLowerInvariant() -ne $ExpectedHead.ToLowerInvariant()) {
    throw "WORKTREE_HEAD_MISMATCH:$Path"
  }
  $dirty = Invoke-Git $Path @('status','--porcelain=v1')
  if ($dirty) { throw "BOOTSTRAP_WORKTREE_NOT_CLEAN:$Path" }
}

function Write-AtomicJson([string]$Path, [object]$Value) {
  $parent = Split-Path -Parent $Path
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  $temp = "$Path.tmp"
  $Value | ConvertTo-Json -Depth 20 -Compress | Set-Content -LiteralPath $temp -Encoding UTF8
  Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Invoke-AuthorityCli([string[]]$Args) {
  $old = $env:PYTHONPATH
  try {
    $env:PYTHONPATH = Join-Path $WorkspaceWorktree 'orchestrator\src'
    $script = Join-Path $WorkspaceWorktree 'orchestrator\scripts\c7r_authority_cli.py'
    $output = @(& $MachinePythonExe $script --key-path $AuthorityKeyPath --key-id $AuthorityKeyId @Args 2>&1)
    if ($LASTEXITCODE -ne 0) {
      throw "AUTHORITY_CLI_FAILED:$($output -join ' ')"
    }
    return ($output -join $NewLine).Trim()
  }
  finally {
    $env:PYTHONPATH = $old
  }
}

function New-UnsignedEnvelope(
  [string]$TaskId,
  [string]$Operation,
  [int]$TaskMinutes = 45,
  [hashtable]$ExtraArguments = @{}
) {
  $now = [DateTimeOffset]::UtcNow
  $arguments = @{ operation = $Operation }
  foreach($key in $ExtraArguments.Keys) { $arguments[$key] = $ExtraArguments[$key] }
  return [ordered]@{
    contract_version = '1.0'
    task_id = $TaskId
    project_id = 'PALWAKF_AGENTIC_AI_SYSTEM'
    project_aliases = @()
    repository_id = $Repository
    executor_id = $ExecutorId
    task_type = 'C7R_PHASE_A'
    mutation_class = 'SERVICE_MUTATION'
    requested_capability_id = 'c7r.phase_a'
    arguments = $arguments
    authority_ref = 'workspace://c7r/pre-gate-a-bootstrap'
    execution_lease = [ordered]@{
      lease_id = "lease-$TaskId"
      task_id = $TaskId
      project_id = 'PALWAKF_AGENTIC_AI_SYSTEM'
      issuer_ref = 'workspace://c7r/pre-gate-a-bootstrap'
      approval_class = 'PRE_GATE_A_BOOTSTRAP'
      allowed_capability_ids = @('c7r.phase_a')
      allowed_mutation_classes = @('SERVICE_MUTATION')
      scope_paths = @($C7RRoot)
      base_sha = $AgenticExpectedHead
      branch = $AgenticBranch
      issued_at = $now.ToString('o')
      expires_at = $now.AddMinutes($TaskMinutes + 15).ToString('o')
      revocation_state = 'ACTIVE'
    }
    expected_remote_head = $AgenticExpectedHead
    expected_base_sha = $AgenticExpectedHead
    task_branch = $AgenticBranch
    scope_paths = @($C7RRoot)
    prohibited_actions = @(
      'main_merge',
      'baseline_promotion',
      'production_mutation',
      'shared_db_mutation',
      'arbitrary_shell'
    )
    idempotency_key = $TaskId.ToLowerInvariant()
    nonce = "$($TaskId.ToLowerInvariant())-nonce"
    issued_at = $now.ToString('o')
    expires_at = $now.AddMinutes($TaskMinutes).ToString('o')
    max_duration_seconds = 1800
    evidence_requirements = @(
      'authority',
      'runtime_admission',
      'zero_manual_terminal',
      'no_normal_api_key_fallback'
    )
    transport_metadata = @{}
    correlation_id = $TaskId.ToLowerInvariant()
    checkpoint_id = $null
    depends_on_task_ids = @()
    model_provider_metadata = @{}
  }
}

function New-SignedTaskFile(
  [string]$TaskId,
  [string]$Operation,
  [hashtable]$ExtraArguments = @{}
) {
  $unsigned = Join-Path $BootstrapRoot "$TaskId.unsigned.json"
  $signed = Join-Path $BootstrapRoot "$TaskId.signed.json"
  $body = Join-Path $BootstrapRoot "$TaskId.issue.md"
  Write-AtomicJson $unsigned (New-UnsignedEnvelope $TaskId $Operation 45 $ExtraArguments)
  $receipt = Invoke-AuthorityCli @('sign','--input',$unsigned,'--output',$signed)
  $envelope = Get-Content -LiteralPath $signed -Raw
  @(
    'PALWAKF_TASK_ENVELOPE_V1_BEGIN'
    $envelope
    'PALWAKF_TASK_ENVELOPE_V1_END'
  ) | Set-Content -LiteralPath $body -Encoding UTF8
  return [pscustomobject]@{ Body=$body; Receipt=$receipt }
}

function Publish-Task([string]$Title, [string]$BodyFile) {
  $url = @(& gh issue create --repo $Repository --title $Title --body-file $BodyFile --label question 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "GITHUB_ISSUE_CREATE_FAILED:$($url -join ' ')" }
  $match = [regex]::Match(($url -join $NewLine), '/issues/(\d+)')
  if (-not $match.Success) { throw "GITHUB_ISSUE_NUMBER_NOT_FOUND" }
  return [int]$match.Groups[1].Value
}

function Wait-ExecutorResult([int]$IssueNumber, [int]$TimeoutSeconds = 180) {
  $deadline = [DateTimeOffset]::UtcNow.AddSeconds($TimeoutSeconds)
  while([DateTimeOffset]::UtcNow -lt $deadline) {
    $raw = @(& gh api "repos/$Repository/issues/$IssueNumber/comments?per_page=100" 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "GITHUB_COMMENTS_READ_FAILED:$IssueNumber" }
    $comments = (($raw -join $NewLine) | ConvertFrom-Json)
    foreach($comment in $comments) {
      $body = [string]$comment.body
      if ($body.StartsWith('PALWAKF_RESULT_V1')) {
        $separator = $Fence + 'json'
        $parts = $body -split [regex]::Escape($separator), 2
        if ($parts.Count -ne 2) { continue }
        $jsonPart = ($parts[1] -split [regex]::Escape($Fence), 2)[0].Trim()
        return ($jsonPart | ConvertFrom-Json)
      }
    }
    Start-Sleep -Seconds 3
  }
  throw "EXECUTOR_RESULT_TIMEOUT:ISSUE=$IssueNumber"
}

function Get-SafeSummary([object]$Evidence) {
  $summary = [string]$Evidence.stdout_hash_or_summary
  $marker = ';SAFE='
  $position = $summary.IndexOf($marker)
  if ($position -lt 0) { throw 'C7R_SAFE_SUMMARY_MISSING' }
  return ($summary.Substring($position + $marker.Length) | ConvertFrom-Json)
}

function Invoke-SignedTask(
  [string]$TaskId,
  [string]$Operation,
  [hashtable]$ExtraArguments = @{}
) {
  $signed = New-SignedTaskFile $TaskId $Operation $ExtraArguments
  $issue = Publish-Task "C7R Phase A - $Operation - $TaskId" $signed.Body
  $evidence = Wait-ExecutorResult $issue
  if ($evidence.exit_state -ne 'COMPLETED') {
    throw "C7R_TASK_NOT_COMPLETED:${Operation}:$($evidence.exit_state):$($evidence.blockers -join ',')"
  }
  return [pscustomobject]@{
    Issue=$issue
    Evidence=$evidence
    Safe=(Get-SafeSummary $evidence)
  }
}

Assert-Command git
Assert-Command gh
if (-not (Test-Path -LiteralPath $MachinePythonExe -PathType Leaf)) {
  throw "MACHINE_PYTHON_NOT_FOUND:$MachinePythonExe"
}
& gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw 'GH_AUTH_NOT_READY' }

New-Item -ItemType Directory -Force -Path $BootstrapRoot | Out-Null
New-DetachedWorktree $WorkspaceRepo $WorkspaceBranch $WorkspaceExpectedHead $WorkspaceWorktree
New-DetachedWorktree $AgenticRepo $AgenticBranch $AgenticExpectedHead $AgenticWorktree

$service = Get-Service -Name $ServiceName -ErrorAction Stop
if ($service.Status -ne 'Stopped') {
  Stop-Service -Name $ServiceName -Force
  $service.WaitForStatus(
    [System.ServiceProcess.ServiceControllerStatus]::Stopped,
    [TimeSpan]::FromSeconds(30)
  )
}

& $MachinePythonExe -m pip install --upgrade "$AgenticWorktree[windows]"
if ($LASTEXITCODE -ne 0) { throw 'AGENTIC_RUNTIME_PACKAGE_INSTALL_FAILED' }

$publicJson = Invoke-AuthorityCli @('public')
$public = $publicJson | ConvertFrom-Json
if ($public.key_id -ne $AuthorityKeyId) { throw 'AUTHORITY_KEY_ID_MISMATCH' }
if ($public.private_key_exportable -ne $false) { throw 'PRIVATE_KEY_EXPORT_POLICY_FAILED' }

$trust = @{}
if (Test-Path -LiteralPath $TrustStorePath) {
  $existing = Get-Content -LiteralPath $TrustStorePath -Raw | ConvertFrom-Json
  foreach($p in $existing.PSObject.Properties) { $trust[$p.Name] = [string]$p.Value }
}
if ($trust.ContainsKey($AuthorityKeyId) -and $trust[$AuthorityKeyId] -ne $public.public_key_b64) {
  throw "AUTHORITY_TRUST_KEY_CONFLICT:$AuthorityKeyId"
}
$trust[$AuthorityKeyId] = [string]$public.public_key_b64
Write-AtomicJson $TrustStorePath $trust

$marker = [ordered]@{
  schema = 'palwakf.c7r.runtime_admission.v1'
  capability_id = 'c7r.phase_a'
  agentic_source_branch = $AgenticBranch
  agentic_source_head = $AgenticExpectedHead.ToLowerInvariant()
  workspace_issuer_branch = $WorkspaceBranch
  workspace_issuer_head = $WorkspaceExpectedHead.ToLowerInvariant()
  authority_key_id = $AuthorityKeyId
  authority_public_key_sha256 = [string]$public.public_key_sha256
  admitted_at = [DateTimeOffset]::UtcNow.ToString('o')
  p3_closed_pass_preserved = $true
  main_mutation = $false
  baseline_promotion = $false
  production_mutation = $false
  shared_db_mutation = $false
}
Write-AtomicJson $RuntimeMarkerPath $marker

Start-Service -Name $ServiceName
(Get-Service -Name $ServiceName).WaitForStatus(
  [System.ServiceProcess.ServiceControllerStatus]::Running,
  [TimeSpan]::FromSeconds(30)
)

$registry = @(& $MachinePythonExe -c "from palwakf_local_agents.outbound_capabilities_v1 import default_capability_registry_v1 as r; d=r().resolve('c7r.phase_a'); print(d.capability_id+'|'+d.mutation_class)" 2>&1)
if ($LASTEXITCODE -ne 0 -or ($registry -join '') -ne 'c7r.phase_a|SERVICE_MUTATION') {
  throw "C7R_RUNTIME_CAPABILITY_READBACK_FAILED:$($registry -join ' ')"
}

$stamp = [DateTimeOffset]::UtcNow.ToString('yyyyMMddHHmmss')
$preflight = Invoke-SignedTask "C7R-PREFLIGHT-$stamp" 'preflight'
if ($preflight.Safe.codex_version -ne '0.159.1') { throw 'C7R_CODEX_VERSION_GATE_FAILED' }
if ($preflight.Safe.agentic_source_head -ne $AgenticExpectedHead.ToLowerInvariant()) {
  throw 'C7R_RUNTIME_HEAD_GATE_FAILED'
}
if ($preflight.Safe.normal_openai_api_key_required -ne $false) {
  throw 'NORMAL_API_KEY_REQUIREMENT_DETECTED'
}

if (-not (Test-Path -LiteralPath $RuntimeConfigPath -PathType Leaf)) {
  throw "RUNTIME_CONFIG_NOT_FOUND:$RuntimeConfigPath"
}
$runtimeConfig = Get-Content -LiteralPath $RuntimeConfigPath -Raw | ConvertFrom-Json
$runtimeConfig.authority_public_keys_b64 = @{}
$runtimeConfig | Add-Member -NotePropertyName authority_public_keys_path -NotePropertyValue $TrustStorePath -Force
Write-AtomicJson $RuntimeConfigPath $runtimeConfig

$terminalTrust = @{}
$terminalTrust[$AuthorityKeyId] = [string]$public.public_key_b64
Write-AtomicJson $TrustStorePath $terminalTrust

Restart-Service -Name $ServiceName -Force
(Get-Service -Name $ServiceName).WaitForStatus(
  [System.ServiceProcess.ServiceControllerStatus]::Running,
  [TimeSpan]::FromSeconds(30)
)

$runtimeConfigReadback = Get-Content -LiteralPath $RuntimeConfigPath -Raw | ConvertFrom-Json
if ($runtimeConfigReadback.authority_public_keys_b64.PSObject.Properties.Count -ne 0) {
  throw 'LEGACY_EMBEDDED_AUTHORITY_KEYS_NOT_TERMINALIZED'
}
$trustReadback = Get-Content -LiteralPath $TrustStorePath -Raw | ConvertFrom-Json
$trustNames = @($trustReadback.PSObject.Properties.Name)
if ($trustNames.Count -ne 1 -or $trustNames[0] -ne $AuthorityKeyId) {
  throw 'DURABLE_AUTHORITY_TRUST_ROOT_READBACK_FAILED'
}

$oauthPrepare = Invoke-SignedTask "C7R-OAUTH-PREPARE-$stamp" 'oauth_prepare'
if ($oauthPrepare.Safe.state -ne 'OAUTH_PENDING') { throw 'C7R_OAUTH_PREPARE_GATE_FAILED' }

$authUrlPath = Join-Path $C7RRoot 'authorization-url.txt'
$deadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
while(-not (Test-Path -LiteralPath $authUrlPath) -and [DateTimeOffset]::UtcNow -lt $deadline) {
  Start-Sleep -Milliseconds 500
}
if (-not (Test-Path -LiteralPath $authUrlPath)) {
  throw 'OAUTH_AUTHORIZATION_URL_NOT_MATERIALIZED'
}
$authUrl = (Get-Content -LiteralPath $authUrlPath -Raw).Trim()
if (-not $authUrl.StartsWith('https://auth.openai.com/api/accounts/authorize?')) {
  throw 'OAUTH_AUTHORIZATION_URL_INVALID'
}
Start-Process $authUrl

$statusPath = Join-Path $C7RRoot 'status.json'
$authDeadline = [DateTimeOffset]::UtcNow.AddMinutes(10)
$authenticated = $false
while([DateTimeOffset]::UtcNow -lt $authDeadline) {
  if (Test-Path -LiteralPath $statusPath) {
    try {
      $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
      if ($status.state -eq 'OAUTH_AUTHENTICATED') {
        $authenticated = $true
        break
      }
      if ($status.state -eq 'OAUTH_FAILED') {
        throw "OAUTH_FAILED_CLOSED:$($status.error)"
      }
    } catch {
      if ($_.Exception.Message -like 'OAUTH_FAILED_CLOSED:*') { throw }
    }
  }
  Start-Sleep -Seconds 2
}
if (-not $authenticated) { throw 'OAUTH_HUMAN_CONSENT_TIMEOUT' }

$oauthStatus = Invoke-SignedTask "C7R-OAUTH-STATUS-$stamp" 'oauth_status'
if ($oauthStatus.Safe.state -ne 'OAUTH_AUTHENTICATED') {
  throw 'C7R_OAUTH_STATUS_GATE_FAILED'
}
if ($oauthStatus.Safe.credential_present -ne $true) {
  throw 'C7R_PROTECTED_CREDENTIAL_GATE_FAILED'
}
if ($oauthStatus.Safe.scopes -notcontains 'chatgpt.tokens.use.direct') {
  throw 'CHATGPT_PLAN_SCOPE_GATE_FAILED'
}

$inference = Invoke-SignedTask "C7R-INFERENCE-$stamp" 'inference'
if ($inference.Safe.state -ne 'COMPLETED') { throw 'C7R_INFERENCE_NOT_COMPLETED' }
if ($inference.Safe.synthetic_response -ne 'PALWAKF_C7R_PHASE_A_OK') {
  throw 'C7R_SYNTHETIC_RESPONSE_GATE_FAILED'
}
if ($inference.Safe.normal_openai_api_key_used -ne $false) {
  throw 'NORMAL_OPENAI_API_KEY_FALLBACK_DETECTED'
}
if ($inference.Safe.normal_codex_api_key_used -ne $false) {
  throw 'NORMAL_CODEX_API_KEY_FALLBACK_DETECTED'
}

[pscustomobject]@{
  BOOTSTRAP = 'PASS'
  P3_CLOSED_PASS_PRESERVED = $true
  WORKSPACE_AUTHORITY_ISSUER = 'PASS'
  PUBLIC_TRUST_KEY_ADMISSION = 'PASS'
  LEGACY_ACCEPTANCE_TRUST_TERMINALIZED = 'PASS'
  C7R_PHASE_A_CAPABILITY = 'PASS'
  C7R_1_AUTHENTICATION_REGISTRATION = 'PASS'
  C7R_2_PROTECTED_CREDENTIAL_MANAGER = 'PASS'
  C7R_3_REAL_SYNTHETIC_CHATGPT_AUTHENTICATED_INFERENCE = 'PASS'
  HARD_GATE_A = 'PASS'
  PREFLIGHT_ISSUE = $preflight.Issue
  OAUTH_PREPARE_ISSUE = $oauthPrepare.Issue
  OAUTH_STATUS_ISSUE = $oauthStatus.Issue
  INFERENCE_ISSUE = $inference.Issue
  MAIN_MUTATION = $false
  BASELINE_PROMOTION = $false
  PRODUCTION_MUTATION = $false
  SHARED_DB_MUTATION = $false
  RDC_BACKBONE = $false
  MANUAL_TERMINAL_NORMAL_PATH = $false
}
