# UAT المطلوبة

1. افتح `/operations?workspace_id=palwakf_government` وتحقق من اسم المساحة والسياسة.
2. أنشئ مسودة محلية واستخدم نفس Idempotency-Key؛ يجب عودة نفس المهمة.
3. بدّل إلى `personal_development`؛ يجب ألا تظهر مهمة PalWakf.
4. حاول الوصول إلى معرف مهمة PalWakf ضمن `personal_development`؛ يجب 404 `WORKSPACE_GOVERNED_TASK_NOT_FOUND`.
5. أكمل Draft → Inbox → Under Review → Approve مع دليل مطلوب؛ تبقى `execution_state=NOT_EXECUTED`.
6. تحقق من عدم وجود طلبات execute / dispatch ومن بقاء model/pilot NONE/NOT_EXECUTED.
