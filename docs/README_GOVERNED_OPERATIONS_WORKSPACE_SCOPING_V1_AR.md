# Governed Operations Workspace Scoping V1

**طبيعة الدفعة:** تطوير محكوم يربط دورة حياة العمليات المحلية بمساحة عمل محددة وسياسة محددة، من دون تشغيل نموذج أو Pilot أو أدوات خارجية.

## النتيجة
- كل عملية تستخدم مسارًا يحتوي `workspace_id`.
- لكل مساحة ملف SQLite منفصل: `workspaces/<workspace_id>/governed_operations.sqlite`.
- لا تُرحّل قاعدة V1 القديمة `audit/governed_operations.sqlite` ولا تُقرأ هنا.
- تقاطع السياسة + ملف الوكيل الأساسي يلتقط مع المهمة كسجل ثابت.
- لا توجد مسارات `execute` أو `dispatch` أو تكامل منصة.
