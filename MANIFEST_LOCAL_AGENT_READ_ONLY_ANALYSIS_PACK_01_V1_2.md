# Manifest

```json
{
  "package": "PALWAKF_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_2_REGISTRY_BOOTSTRAP_CLOSURE",
  "version": "1.2.0",
  "candidate_status": "NOT_INSTALLED_NOT_VERIFIED",
  "supersedes": "PALWAKF_LOCAL_AGENT_READ_ONLY_ANALYSIS_PACK_01_V1_1_PARSE_SAFETY_REPLACEMENT",
  "previous_package_apply_status": "NOT_APPLIED_REGISTRY_BOOTSTRAP_BLOCKED",
  "grounded_registry_schema": [
    "agent_id",
    "allowed_autonomy",
    "runtime_enabled",
    "runtime_mode",
    "allowed_skills",
    "forbidden_capabilities"
  ],
  "bootstrap_target": "documentation_handoff",
  "knowledge_researcher_transition": "admission_required -> read_only_report_only",
  "core_runtime_mutation": "NONE",
  "model_execution": "DISABLED_BY_DEFAULT",
  "platform_mutation": "NONE",
  "database_access": "NONE",
  "git_write": "NONE",
  "deployment": "NONE",
  "secrets_access": "NONE",
  "memory_write": "NONE",
  "files": [
    {
      "path": "PROJECT_STATUS_AR.md",
      "sha256": "5923e158f6ddd72c72f5e53f0069e3d9c8701f3ba8dec20d1088a2f2461fd6fb",
      "bytes": 597
    },
    {
      "path": "README_AR.md",
      "sha256": "f53ff8623904b3745c2c13727868688ee15a8ed91ac11b5d440b97d8a071ca0e",
      "bytes": 1807
    },
    {
      "path": "ROOT_CAUSE_AND_REMEDIATION_AR.md",
      "sha256": "329300f4d054effefe5e7a9b10b775e78d6c962b66dbfb27bf596d1702b113ae",
      "bytes": 1051
    },
    {
      "path": "SCOPE_AND_LIMITATIONS_AR.md",
      "sha256": "56e74dc4504187c1a35a714f153832a6d780f0e47777be6567a1947e05831111",
      "bytes": 1185
    },
    {
      "path": "agents/charters/read_only_analysis_pack_01/COORDINATOR_READ_ONLY_ANALYSIS_PACK_01.md",
      "sha256": "ce8b06a743ffc59fa4f2b4382705f49907262d7837cecc1672de0776c607970d",
      "bytes": 913
    },
    {
      "path": "agents/charters/read_only_analysis_pack_01/DOCUMENTATION_HANDOFF_READ_ONLY_ANALYSIS_PACK_01.md",
      "sha256": "0016ca3646a8875e7e05e9722b3c74ccfbf26f77c48a6b3390d4c3bfecc79a1b",
      "bytes": 828
    },
    {
      "path": "agents/charters/read_only_analysis_pack_01/KNOWLEDGE_RESEARCHER_READ_ONLY_ANALYSIS_PACK_01.md",
      "sha256": "4242b2b8523842634bc3c542736e28da5a0038fe1ca9e518f104b669dec06338",
      "bytes": 869
    },
    {
      "path": "agents/charters/read_only_analysis_pack_01/SOVEREIGNTY_REVIEWER_READ_ONLY_ANALYSIS_PACK_01.md",
      "sha256": "cca5f42beef4e753c2246d4e27f1642348fa7a5169a080821884a0ef2a2e55e9",
      "bytes": 838
    },
    {
      "path": "agents/output_profiles/read_only_analysis_pack_01/coordinator.json",
      "sha256": "c8f6b26fcc537764df8c2b142d19f421db064574516a1fc1ff0bbd02394df61f",
      "bytes": 411
    },
    {
      "path": "agents/output_profiles/read_only_analysis_pack_01/documentation_handoff.json",
      "sha256": "6a6ab6dcba5a54f4485615302033aa9761e8c7978020a84ce6f2589e67df81d6",
      "bytes": 415
    },
    {
      "path": "agents/output_profiles/read_only_analysis_pack_01/knowledge_researcher.json",
      "sha256": "ba2461042400893bc5db6c9c3b0054c60e03359263e0c8cb379b36307ab909d1",
      "bytes": 423
    },
    {
      "path": "agents/output_profiles/read_only_analysis_pack_01/sovereignty_reviewer.json",
      "sha256": "982568452b56ce86253b667d50626fb65e8cdbb9d9859327dff0a0c2451a491a",
      "bytes": 419
    },
    {
      "path": "governance/read_only_analysis_pack_01/PACK_01_POLICY.md",
      "sha256": "a434f592775522f6e07dc66205cb49ef132fea7a14d828facd45bcfb83d4fad9",
      "bytes": 901
    },
    {
      "path": "governance/read_only_analysis_pack_01/PARSE_SAFETY_POLICY_V1_1.md",
      "sha256": "e79297896fc7329c6211d49b6e2d6b997606634d121edb0cb74e9314f18a567f",
      "bytes": 492
    },
    {
      "path": "governance/read_only_analysis_pack_01/REGISTRY_BOOTSTRAP_CONTRACT_V1_2.md",
      "sha256": "c2404240167718996cb23fe4721972c21ad3d3eaeb9dc4f550df1838cb8eaef7",
      "bytes": 1239
    },
    {
      "path": "scripts/Install-ReadOnlyAnalysisPack01V1_2.ps1",
      "sha256": "1942f741cf30ee61f383027ce1f753a393798458f35221cf7ce53e406dabdefe",
      "bytes": 11280
    },
    {
      "path": "scripts/Invoke-ReadOnlyAnalysisPack01EvalsV1_2.ps1",
      "sha256": "9ba93d0b5f68d213adaa24f3afcc1a1d577fc036799023d22ef1067e5ef78b1f",
      "bytes": 3641
    },
    {
      "path": "scripts/New-ReadOnlyAnalysisPack01PilotTasksV1_2.ps1",
      "sha256": "9f3517d683d96486a909d873d598bf90fabc16351670415e4902a576eb055ff0",
      "bytes": 2355
    },
    {
      "path": "scripts/Restore-ReadOnlyAnalysisPack01RegistryBackupV1_2.ps1",
      "sha256": "0e2ab8fe932675cf23f46254efe031a534e25cde1216231028f5b481fe989f26",
      "bytes": 968
    },
    {
      "path": "scripts/Test-ReadOnlyAnalysisPack01PackageSyntaxV1_1.ps1",
      "sha256": "c2556ec8faa6c5cc36719941e343e659e6e4e8a73c019c6a5118ac7b4c4068b7",
      "bytes": 1610
    },
    {
      "path": "scripts/Test-ReadOnlyAnalysisPack01PreflightV1_2.ps1",
      "sha256": "770558c829385555ecea69a9448650ed446b23f5b1d0faaf735cbcf0e6f21d97",
      "bytes": 4260
    },
    {
      "path": "scripts/Test-ReadOnlyAnalysisPack01V1_2.ps1",
      "sha256": "33e111253fcaf4b89f76ccc760f03f5dad6f4e4d733e1b5885262103f7768f12",
      "bytes": 5323
    },
    {
      "path": "tasks/templates/read_only_analysis_pack_01/PACK01_COORDINATOR_ROUTING_PILOT_001.json",
      "sha256": "b67f3c9d7d0472ab3a2aeeff6f7f2b8c121dfd36aa333623faf73a601a09d719",
      "bytes": 978
    },
    {
      "path": "tasks/templates/read_only_analysis_pack_01/PACK01_DOCUMENTATION_HANDOFF_PILOT_001.json",
      "sha256": "c7bdb9e400c6cd0cc633f894f97a017618a1c2e7337a72ca86adf2a3e222bc88",
      "bytes": 987
    },
    {
      "path": "tasks/templates/read_only_analysis_pack_01/PACK01_KNOWLEDGE_RESEARCH_PILOT_001.json",
      "sha256": "48180306963dbeb39d2ca0a738495157527863e7007773e40a48c2bb0f7c0361",
      "bytes": 973
    },
    {
      "path": "tasks/templates/read_only_analysis_pack_01/PACK01_SOVEREIGNTY_REVIEW_PILOT_001.json",
      "sha256": "a5a188430a7d4a409042cdce11e20a3d59fbb4900ae84380c808964fa8e54d10",
      "bytes": 976
    }
  ]
}
```
