# Local Agent Read-Only Analysis Pack 01 Policy

## Scope
This pack provisions four local roles for L0 read-only, report-only pilots:
coordinator, sovereignty_reviewer, knowledge_researcher, documentation_handoff.

## Fixed core boundary
The pack must not alter:
- runtime/ReadOnlyRuntimeContextEvidenceV1.psm1
- scripts/Invoke-ReadOnlyContextEvidenceRunnerV1.ps1
- scripts/Invoke-ReadOnlyEvidenceGatewayV1.ps1
- task_contracts/MODEL_OUTPUT_CONTRACT_V1.json

## Agent boundary
- Approved local references only.
- task_triage and evidence_assessment only.
- L0_READ_ONLY, report-only runtime mode, human review required.
- No platform/database/Git/deployment/secrets/memory writes.

## Activation
Generated tasks remain PENDING_HUMAN_APPROVAL until explicitly approved through the existing approval gate.
Model execution is not performed by installation, static tests, evaluations, or task generation.
