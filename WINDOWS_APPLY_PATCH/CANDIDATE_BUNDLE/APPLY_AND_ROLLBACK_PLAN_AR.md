# خطة Apply وRollback

## Apply

1. فك الحزمة في `%TEMP%` أو مسار مستقل.
2. شغّل `scripts/Apply-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1` مع `-ProjectRoot`.
3. شغّل Static Gate من داخل المشروع.
4. شغّل Runner في Worktree معزول.

## Rollback

لا تستخدم rollback إلا إذا فشل Static Gate أو UAT أو ظهر diff خارج النطاق. مرر `BACKUP_ROOT` الناتج من Apply إلى:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  "<bundle>\scripts\Rollback-LegacyTestContractMigrationAndPositiveAuthorizationUatV1.ps1" `
  -BackupRoot "<BACKUP_ROOT>"
```

## الحدود

الـRunner ينسخ المشروع إلى `output/.../isolated_worktree` ويشغّل pytest هناك. لا يقبل تعديل المصدر الحقيقي أثناء UAT.
