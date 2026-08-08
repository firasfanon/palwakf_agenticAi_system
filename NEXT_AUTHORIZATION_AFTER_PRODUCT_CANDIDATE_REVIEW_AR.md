# التفويض التالي بعد مراجعة المرشح

بعد مراجعة صور التصميم وملفات المرشح، توجد خطوتان منفصلتان فقط:

## 1) Apply محكوم داخل isolated worktree

```text
AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_APPLY_V1_ISOLATED_WORKTREE_ONLY
```

لا يشمل هذا التفويض UAT أو FastAPI runtime أو كتابة React أو نموذج أو Pilot أو تجاري.

## 2) UAT بصري Read-Only على Windows

لا يبدأ إلا بعد نجاح Apply وإظهار `STATIC_GATE_PASS`:

```text
AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_VISUAL_UAT_V1_ISOLATED_WORKTREE_ONLY
```

لا يوجد تفويض مناسب حاليًا لـCommercial Client Scope Apply؛ يبقى مؤجلًا حتى اعتماد تصميم الواجهة وتحقق UAT read-only.
