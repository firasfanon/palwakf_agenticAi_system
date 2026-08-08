param(
  [Parameter(Mandatory=$true)][string]$PackageRoot,
  [Parameter(Mandatory=$true)][string]$ProjectRoot,
  [Parameter(Mandatory=$true)][string]$PreflightManifest,
  [switch]$WhatIf,
  [switch]$Apply
)
$ErrorActionPreference='Stop'
if($Apply){throw 'APPLY_NOT_INCLUDED_IN_IDEMPOTENCY_REPAIR_CANDIDATE'}
if(-not $WhatIf){throw 'WHATIF_REQUIRED_FOR_REPAIR_CANDIDATE'}
$contractPath=Join-Path $PackageRoot 'contracts\master_batch_contract_v1.json'
$contract=Get-Content -LiteralPath $contractPath -Raw -Encoding UTF8 | ConvertFrom-Json
$preflight=Get-Content -LiteralPath $PreflightManifest -Raw -Encoding UTF8 | ConvertFrom-Json
if($preflight.manifest_binding_schema_version -ne '2'){throw 'PREFLIGHT_MANIFEST_SCHEMA_VERSION_MISMATCH'}
if($preflight.failure_count -ne 0){throw 'PREFLIGHT_MANIFEST_NOT_CLEAN'}
if($preflight.package_id -ne $contract.package_id){throw 'PREFLIGHT_PACKAGE_ID_MISMATCH'}
if($preflight.project_root -ne (Resolve-Path -LiteralPath $ProjectRoot).Path){throw 'PREFLIGHT_PROJECT_ROOT_MISMATCH'}
$expectedScriptHash=(Get-FileHash -LiteralPath (Join-Path $PackageRoot 'scripts\Test-UnifiedGovernedCapabilityFoundationIdempotentPreflight.ps1') -Algorithm SHA256).Hash
if($preflight.preflight_script_sha256 -ne $expectedScriptHash){throw 'PREFLIGHT_SCRIPT_HASH_MISMATCH'}
$expectedContractHash=(Get-FileHash -LiteralPath $contractPath -Algorithm SHA256).Hash
if($preflight.contract_sha256 -ne $expectedContractHash){throw 'PREFLIGHT_CONTRACT_HASH_MISMATCH'}
$states=$preflight.component_states
$writeGov=if($states.government_manifest.state -eq 'PREIMAGE_EXPECTED'){1}else{0}
$writeSource=if($states.governed_capability_source_and_test.state -eq 'PREIMAGE_EXPECTED'){6}else{0}
$writePilot=if($states.pilot_config.state -eq 'PREIMAGE_EXPECTED'){1}else{0}
$writeLedgerSeed=if($states.evidence_ledger.state -eq 'PREIMAGE_EXPECTED'){2}else{0}
$writeApp=if($states.app_mount.state -eq 'PREIMAGE_EXPECTED'){1}else{0}
$initializeDb=if($states.foundation_databases.state -eq 'PREIMAGE_EXPECTED'){3}else{0}
$ledgerEvents=if($initializeDb -gt 0){3}else{0}
'===== UNIFIED GOVERNED CAPABILITY FOUNDATION IDEMPOTENT WHATIF ====='
'WHATIF_STATUS=COMPLETE'
'WHATIF_MODE=TRUE'
'TARGET_MUTATION_SCOPE=RECONCILE_PREIMAGE_ONLY_AND_PRESERVE_EXACT_POSTIMAGES'
("PREDICTED_GOVERNMENT_MANIFEST_WRITE_COUNT={0}" -f $writeGov)
("PREDICTED_CAPABILITY_SOURCE_FILE_COUNT={0}" -f $writeSource)
("PREDICTED_PILOT_CONFIG_WRITE_COUNT={0}" -f $writePilot)
("PREDICTED_EVIDENCE_LEDGER_SEED_WRITE_COUNT={0}" -f $writeLedgerSeed)
("PREDICTED_APP_ENTRYPOINT_MUTATION_COUNT={0}" -f $writeApp)
("PREDICTED_WORKSPACE_FOUNDATION_SQLITE_COUNT={0}" -f $initializeDb)
("PREDICTED_LEDGER_EVENT_APPEND_COUNT={0}" -f $ledgerEvents)
('RECONCILIATION_COMPONENTS=' + (($states.psobject.Properties | ForEach-Object { "{0}:{1}" -f $_.Name,$_.Value.state }) -join ','))
'MB6_MODEL_PROMPT_DURING_APPLY=NONE'
'MODEL_EXECUTION=NONE'
'PILOT_EXECUTION=NOT_EXECUTED'
'SHELL_EXECUTION=NONE'
'GIT_WRITE=NONE'
'DEPLOYMENT=NONE'
'EXTERNAL_NETWORK=NONE'
'PROJECT_MUTATION=NONE_DURING_WHATIF'
