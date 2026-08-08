# Manifest

```json
{
  "batch_id": "MEGA_BATCH_LOCAL_AGENTS_GOVERNED_OPERATIONS_WORKBENCH_AUDIT_ASSURANCE_V2",
  "status": "CANDIDATE_PREPARED_NOT_APPLIED",
  "baseline_required": "Governed Operations Foundation V1 with reconciled Browser JS postimage and Command Center event-listener postimage",
  "mutation_scope": {
    "source_files": [
      "backend/src/palwakf_local_agents/governed_operations/__init__.py",
      "backend/src/palwakf_local_agents/governed_operations/contracts.py",
      "backend/src/palwakf_local_agents/governed_operations/store.py",
      "backend/src/palwakf_local_agents/governed_operations/router.py",
      "backend/src/palwakf_local_agents/governed_operations/static/index.html",
      "backend/src/palwakf_local_agents/governed_operations/static/styles.css",
      "backend/src/palwakf_local_agents/governed_operations/static/app.js",
      "backend/tests/test_governed_operations.py"
    ],
    "docs_destination": "docs/governed_operations/workbench_audit_assurance_v2",
    "app_entrypoint": "NONE",
    "command_center": "NONE",
    "sqlite_install_write": "NONE",
    "sqlite_runtime_migration": "V2 on first governed-operations access"
  },
  "features": [
    "Operational intake workbench",
    "Task lifecycle workspace",
    "Human review attestation",
    "Expected-version optimistic concurrency",
    "Evidence category approval gate",
    "Task and global audit hash-chain verification",
    "Activity ledger",
    "Task bundle and readiness APIs",
    "Arabic RTL responsive operations UI"
  ],
  "safety": {
    "model_execution": "NONE",
    "pilot_execution": "NOT_EXECUTED",
    "execution_gateway": "DISABLED_BY_DEFAULT",
    "platform_mutation": "NONE",
    "external_database_access": "NONE",
    "git_write": "NONE",
    "deployment": "NONE",
    "secrets_access": "NONE",
    "memory_write": "NONE"
  },
  "preimage_hashes": {
    "backend/src/palwakf_local_agents/governed_operations/__init__.py": "7552AFBAB693E7E7A13D11EE81146027059175F1BFA66DBDEA9F448DBABD95F3",
    "backend/src/palwakf_local_agents/governed_operations/contracts.py": "BC5E26AA7233A047867A78B2C87179A168C047315ADBE495D53C5530479FEDC8",
    "backend/src/palwakf_local_agents/governed_operations/store.py": "47078813C1CDCDFD2B09971458E03F3D60F73E37DFCB62FB2796289FB90B7207",
    "backend/src/palwakf_local_agents/governed_operations/router.py": "5E192F04EE75B603193D734324D6D24BA5B443917F4FDC6F86FE8B015B656810",
    "backend/src/palwakf_local_agents/governed_operations/static/index.html": "57B681746E299739675D8028301945A968A92D5757F154129CF058AC6799BA45",
    "backend/src/palwakf_local_agents/governed_operations/static/styles.css": "E110BF2A9CB6CD6ECF658C62D5754FA174CEF52EA2570CE745B9ECAA81D1C52B",
    "backend/src/palwakf_local_agents/governed_operations/static/app.js": "9379BD8826DF41AF456B601A578EDF294E9DDD029B2F4EED242DFD9B102FF041",
    "backend/tests/test_governed_operations.py": "B1051D5952AC6460E1B322DE938DB443A36B7E98D34A79AC2E7FACFEA7C499E6"
  },
  "postimage_hashes": {
    "backend/src/palwakf_local_agents/governed_operations/__init__.py": "7552AFBAB693E7E7A13D11EE81146027059175F1BFA66DBDEA9F448DBABD95F3",
    "backend/src/palwakf_local_agents/governed_operations/contracts.py": "89737209BB4D4BD1E1752FA9B0507EEA6F24322BDBA1CBCA03662FAB4981E49F",
    "backend/src/palwakf_local_agents/governed_operations/store.py": "FB41112EA03825A6D4231F69951810D9B8C235DDB1A21DD9487EC09D77C0122D",
    "backend/src/palwakf_local_agents/governed_operations/router.py": "B239E66B92411922D532D919566719D8FF32087CB692F23DEBAFC9D5374A0D26",
    "backend/src/palwakf_local_agents/governed_operations/static/index.html": "75585CB65F5A3764DA908B1A9F36ED92228DC5E0EE04B597DCBCC0A07D68F67B",
    "backend/src/palwakf_local_agents/governed_operations/static/styles.css": "267442695DDEED37F155956212AB8DA01B7CC73E026B39EA3E9E633962BC4F7E",
    "backend/src/palwakf_local_agents/governed_operations/static/app.js": "295AF44E200BE98358A8FED27DC65861409981858927CABA6840E392C7DD80C8",
    "backend/tests/test_governed_operations.py": "764B4F80A9E82E67B385FC4D1BFBA915BFA097224630C6452DBAF6B618A55EC6"
  },
  "tests_run": {
    "pytest": "5 passed",
    "node_check": "pass"
  }
}
```
