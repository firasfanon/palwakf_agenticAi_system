[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Users\DELL\StudioProjects\palwakf_local_agents",
  [string]$OutputRoot = "D:\PALWAKF_ASSISTANT_BASELINES",
  [string]$Python = "python",
  [string]$Origin = "http://127.0.0.1:8010",
  [ValidateSet("ollama", "openai_compatible")][string]$Provider = "ollama",
  [string]$ProviderBaseUrl = "http://127.0.0.1:11434",
  [string]$Model = "qwen2.5:3b",
  [int]$TimeoutSeconds = 180,
  [int]$MaxOutput = 1200,
  [double]$Temperature = 0.0,
  [string]$AuthorizationToken = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$expectedToken = "AUTHORIZE_LOCAL_AGENTS_GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_LOOPBACK_ONLY_V1"
if ([string]::IsNullOrWhiteSpace($AuthorizationToken)) { throw "NEW_RETRY_AUTHORIZATION_TOKEN_REQUIRED" }
if ($AuthorizationToken -ne $expectedToken) { throw "NEW_RETRY_AUTHORIZATION_TOKEN_MISMATCH" }
$token = $AuthorizationToken
$script = Join-Path $PSScriptRoot "scripts\run_governed_live_probe_v1.py"
& $Python $script `
  --project-root $ProjectRoot `
  --output-root $OutputRoot `
  --origin $Origin `
  --provider $Provider `
  --provider-base-url $ProviderBaseUrl `
  --model $Model `
  --timeout-seconds $TimeoutSeconds `
  --max-output $MaxOutput `
  --temperature $Temperature `
  --authorization $token `
  --execute-live
if ($LASTEXITCODE -ne 0) { throw "AUTHORIZED_LIVE_PROBE_FAILED=$LASTEXITCODE" }
Write-Host "AUTHORIZED_LIVE_PROBE_WRAPPER=PASS"
