# خطة تطبيق واسترجاع لاحقة — ممنوع التنفيذ ضمن هذه الدفعة

## النطاق المسموح عند تفويض Apply مستقل

- إنشاء `isolated worktree` من المصدر المعتمد.
- فحص preimage لمكونات `PATCH_MANIFEST.json`.
- نسخ **سبعة** ملفات React فقط من `PATCH_PAYLOAD/` إلى الـworktree.
- تشغيل Static Gate ثم `npm ci --ignore-scripts` و`npm run check` و`npm run build` في الـworktree.
- لا تبدأ FastAPI ولا تغيّر `frontend/dist` في المصدر الأصلي.

## النطاق المحظور

```text
NO_BACKEND_PATCH
NO_FASTAPI_ROUTE_CHANGE
NO_SQLITE_MIGRATION
NO_REACT_WRITE_UI
NO_ACTOR_OR_CLIENT_TOKEN
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_COMMERCIAL_APPLY
NO_PRODUCTION
```

## الاسترجاع

لأن المرشح لا يلمس المصدر الآن، لا يوجد rollback مطلوب. عند Apply مستقبلي داخل worktree فقط:

1. احذف الـworktree أو استبدل الملفات السبعة بنسخ preimage الموثقة.
2. احذف `frontend/node_modules` و`frontend/dist` داخل الـworktree إذا لزم.
3. تحقق أن Git/source project الأصلي لم يتغير.
4. لا ترحّل أو تسترجع SQLite؛ لا توجد migration في هذه الحزمة.

## بوابة ما بعد Apply

نجاح build لا يكفي لقبول baseline. يلزم تفويض UAT بصري Read-Only منفصل على Windows، ثم تقييم لقطات ومسارات Network وDOM حسب الـrunbook.
