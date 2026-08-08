# فصل منظومة المساعدين عن مشروع المنصة

## القرار
يبقى مشروع `palwakf` منصة المنتج: Flutter وSupabase والعقود والأنظمة.  
ينشأ هذا المشروع المستقل لتشغيل المساعدين المحليين وواجهة التشغيل والسجل المحلي.

## ما يبقى داخل palwakf
- `docs/ai`: عقود أو قرارات تخص المنصة نفسها.
- `local_agents`: ملفات مرجعية قديمة أو موجزة، لا Runtime ولا SQLite ولا Python environment.

## ما ينتقل أو يُنسخ إلى هذا المشروع
- Prompts وRegistry وPolicies التشغيلية.
- تقارير الأدلة ومهام المساعدين.
- Backend محلي، Console، SQLite audit store، Workspaces.

## قاعدة النقل
الاستيراد Copy-only من المصدر إلى `reference_sources/platform_snapshot/`.  
لا حذف للمصدر، ولا تعديل للمنصة، ولا Git action داخل `palwakf`.
