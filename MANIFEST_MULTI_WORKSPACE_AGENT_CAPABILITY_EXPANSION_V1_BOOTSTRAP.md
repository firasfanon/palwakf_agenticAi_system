# Manifest — Preflight Anchor Reconciliation Repair Candidate

```text
PACKAGE=PALWAKF_LOCAL_AGENTS_MEGA_BATCH_MULTI_WORKSPACE_AGENT_CAPABILITY_EXPANSION_V1_PREFLIGHT_ANCHOR_RECONCILIATION_REPAIR_CANDIDATE
TYPE=PACKAGE_SIDE_VALIDATION_REPAIR
REPAIR_SCOPE=PREFLIGHT_ANCHOR_REGEX_ONLY
PROJECT_SOURCE_MUTATION=NONE
BOOTSTRAP_TEMPLATE_MUTATION=NONE
INSTALLER_LOGIC_MUTATION=NONE
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
```

## الملفات المعدلة داخل الحزمة

- `scripts/Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapPreflight.ps1`
- `scripts/Test-MultiWorkspaceAgentCapabilityExpansionV1BootstrapCandidateSyntax.ps1`
- `candidate/repair_scope.json`
- الوثائق و`PACKAGE_INVENTORY.json`

## الملفات غير المعدلة مقارنة بحزمة Bootstrap السابقة

- قوالب `workspace_manifest.json` للمساحات الثلاث.
- `accepted_baseline_hashes_v1.json`.
- `workspace_capability_matrix_v1.json`.
- `Install-MultiWorkspaceAgentCapabilityExpansionV1Bootstrap.ps1`.

## الضمانات

يبقى WhatIf قراءة/محاكاة فقط. ولا يكتب المشروع أي ملف قبل `-Apply` مع تفويض مستقل.
