# Guide Update Snippet — PalWakf Local Agents

أضف النص التالي إلى `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` **فقط بعد وضعه في المرجع الحاكم ومراجعة دليل UAT اللاحق**:

> في 2026-07-06 نُفّذ `AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_APPLY_V1_ISOLATED_WORKTREE_ONLY` داخل worktree معزول مستخرج من دليل baseline المقبول. حُصرت التعديلات في 7 ملفات React/TypeScript لواجهة `/agent-console`، واجتازت preimage/postimage، وStatic Read-Only Gate، و`npm ci --ignore-scripts --offline`، و`tsc --noEmit`، و`vite build`. لا تعديل للمصدر الأصلي على Windows، ولا FastAPI runtime، ولا SQLite، ولا Token، ولا React write، ولا نموذج أو Pilot أو Commercial Apply. هذا دليل Apply داخل worktree فقط؛ baseline الرسمي لم يُرفع لأن UAT البصري/الشبكي على Windows ما زال مطلوبًا.

**ملاحظة حاكمة:** لم يُرفق ملف `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` نفسه، لذا أُنتج هذا المقتطف ولم يُدمج مباشرة.
