# Changelog — Windows UAT Runner Worktree Cleanup Repair V8

- السبب: ملف `journal.baj` ظل مقفلاً بعد إغلاق/استخدام Edge المرئي، فأخفق حذف الـworktree في مرحلة التنظيف.
- التعديل: إغلاق موجّه فقط لعمليات Edge/Chrome المرتبطة بملفات تعريف المتصفح داخل الـworktree، ثم حذف مع خمس محاولات موثقة.
- لا تغيير في React، FastAPI، lockfile، أو سياسة read-only.
- baseline: غير محدّث؛ ينتظر نجاح UAT النهائي والأرشيف.
