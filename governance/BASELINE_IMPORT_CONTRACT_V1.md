# عقد استيراد المراجع من PalWakf

الاستيراد في V1 ينسخ فقط ملفات محددة من:
- `docs/ai`
- `local_agents`

الوجهة:
- `reference_sources/platform_snapshot/docs_ai`
- `reference_sources/platform_snapshot/local_agents`

محظورات:
- لا حذف أو rename في المصدر.
- لا تعديل Flutter/Supabase.
- لا نسخ `.env` أو أسرار أو قواعد بيانات.
- لا اعتبار الملفات المستوردة دليل تشغيل حي.
