# Session Handoff — Local Agents Product Start Screen Read-Only Apply

## نقطة الاستئناف

أُنجز Apply داخل worktree معزول مشتق من دليل baseline. جميع فحوصات المصدر والبناء ناجحة، لكن `WINDOWS_RUNTIME_UAT` لم ينفذ.

## الحالة الحاكمة

```text
APPLY_EVIDENCE_DERIVED_WORKTREE_PASS__WINDOWS_RUNTIME_UAT_PENDING__BASELINE_NOT_ACCEPTED
```

## لا تغير هذه الحزمة

- مشروع Windows الأصلي.
- SQLite أو FastAPI أو route mount.
- Tokens أو credentials أو كتابة React.
- النموذج أو Pilot أو نطاق العملاء التجاري.

## الدليل الحاسم

- `EVIDENCE/APPLY_FILE_HASH_REPORT.json`
- `EVIDENCE/SOURCE_SCOPE_DIFF_REPORT.json`
- `EVIDENCE/STATIC_READ_ONLY_GATE_REPORT.json`
- `EVIDENCE/NPM_CI_OFFLINE.log`
- `EVIDENCE/TSC_NO_EMIT.log`
- `EVIDENCE/VITE_BUILD.log`

## التفويض التالي فقط

`AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY`

ينفذ في Windows وعلى الـworktree فقط: FastAPI local runtime + browser screenshots + HAR/network summary + DOM/console evidence. لا يسمح بكتابة React أو SQLite أو تشغيل نموذج أو Pilot أو إنتاج.
