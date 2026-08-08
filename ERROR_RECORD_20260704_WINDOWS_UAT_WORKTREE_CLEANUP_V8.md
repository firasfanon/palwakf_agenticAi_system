# Error Record — WORKTREE_CLEANUP / journal.baj

## الحالة
- Run: `WINDOWS_LOCAL_BROWSER_UAT_20260703T221443Z`
- السجل وصل بنجاح إلى: `NPM_CI`, `TYPESCRIPT_CHECK`, `VITE_BUILD`, `FASTAPI_RUNTIME`, `HTTP_RUNTIME_UAT`, `HEADLESS_BROWSER_RENDER_CAPTURE`, `VISIBLE_BROWSER_OPENED`.
- الفشل: `Remove-Item` على worktree؛ الملف `journal.baj` كان مستخدمًا من عملية أخرى.

## السبب
ملف تعريف Edge المرئي محفوظ داخل الـworktree، والإصدار السابق لا ينهي العمليات التابعة له قبل الحذف.

## الحل
V8 ينهي فقط عمليات المتصفح المطابقة لمسار `--user-data-dir` للـprofile المعزول ثم يحاول الحذف خمس مرات مع evidence logs.

## baseline
لا تغيير baseline؛ يلزم run نهائي ناجح مع archive وSHA-256.
