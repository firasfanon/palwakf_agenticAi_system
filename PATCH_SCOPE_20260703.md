# PATCH SCOPE — 20260703

```text
APPROVED_FILE_COUNT = 2
OBSERVED_FILE_COUNT = 2
RESULT = PASS
```

## الملفات

1. `backend/src/palwakf_local_agents/app.py`
2. `frontend/src/api/client.ts`

## سبب كل تعديل

- الأول يمنع فشل التفعيل الشرطي لـReact عندما يتوفر dist الحقيقي لاحقًا، ويشترط `assets` لتفادي mount إلى دليل غير موجود.
- الثاني يمنع إرفاق Cookies تلقائيًا في عميل React الحالي للقراءة فقط.

## ممنوع ضمن هذا Patch

```text
No API write changes
No router schema changes
No SQLite changes
No model changes
No frontend build
No runtime server
```
