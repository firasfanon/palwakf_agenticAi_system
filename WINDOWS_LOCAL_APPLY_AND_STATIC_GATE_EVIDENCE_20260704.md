# Windows Local Apply + Static Gate Evidence — 2026-07-04

## المصدر
نص مخرجات PowerShell الذي قدّمه المستخدم من جهاز Windows ضمن المسار:

```text
C:\Users\DELL\StudioProjects\palwakf_local_agents
```

## تطبيق الإصلاح

```text
PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
BACKUP_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents\backups\har_filename_reconciliation_v1_20260704_015540
RUNNER_PREIMAGE_SHA256=E0485D2FBA09DC2CEB6F269C59220C030FABBE451BA760BE81F4631955D966E5
STATIC_GATE_PREIMAGE_SHA256=8384DC6E9C1CE0289B3AC46BDFE99F01494159EF0636DB054C151C13AE4874E1
RUNNER_PARSER_ERROR_COUNT=0
STATIC_GATE_PARSER_ERROR_COUNT=0
HAR_FILENAME_RECONCILIATION_V1=PASS
```

## Static Gate

```text
REQUIRED_ITEM_COUNT=10
MISSING_ITEM_COUNT=0
RUNNER_PARSER_ERROR_COUNT=0
LOCKFILE_INTERNAL_REGISTRY_RESOLVED_COUNT=0
LOCKFILE_PUBLIC_REGISTRY_RESOLVED_COUNT=113
runner_parser_error_count_zero=True
runner_project_root_default_safe=True
react_credentials_omit=True
react_get_only_literal=True
react_no_authorization_literal=True
react_no_web_storage_literal=True
app_loopback_default=True
app_react_conditional_mount=True
runner_isolated_worktree=True
runner_forces_safe_flags=True
runner_has_har_gate=True
runner_has_har_filename_reconciliation=True
runner_rejects_ambiguous_har_evidence=True
runner_has_cleanup=True
runner_scopes_browser_cleanup_to_isolated_profile=True
runner_retries_worktree_cleanup=True
runner_uses_npm_cmd=True
runner_captures_process_stderr_by_exit_code=True
runner_headless_capture_avoids_stderr_pipeline=True
lockfile_no_internal_build_registry=True
lockfile_has_public_registry_resolved_urls=True
runner_registry_mode_forces_public_registry=True
runner_registry_mode_uses_isolated_cache=True
FINAL_RESULT=PASS
```

## التفسير
التطبيق المحلي لـHAR Filename Reconciliation V1 والبوابة الساكنة اجتازا. لا توجد إعادة UAT في هذا النطاق؛ قبول Browser UAT للقراءة فقط يبقى مؤسسًا على أرشيف الأدلة المستقل السابق `WINDOWS_LOCAL_BROWSER_UAT_20260703T222811Z.zip`.
