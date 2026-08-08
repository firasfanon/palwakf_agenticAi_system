# تحديث مقترح للمرجع الحاكم PalWakf

> لم يكن ملف `PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md` موجودًا ضمن baseline المتاح؛ لذلك هذا نص إدراج فقط ولا يدعي تعديل المرجع الأعلى.

## Local Agents — Windows Browser UAT Runtime Evidence V1

- أضيف Runner محلي لويندوز يعمل داخل Worktree مؤقت ولا يشغّل التطبيق على مصدر المشروع الأصلي.
- يفرض `127.0.0.1` و`ALLOW_AGENT_EXECUTION=false` و`ALLOW_PLATFORM_MUTATION=false` و`ALLOW_DATABASE_ACCESS=false`.
- يجمع health, HTTP, screenshot, DOM, HAR, SHA-256 archive evidence.
- لا يتحول baseline إلى `UAT_ACCEPTED` قبل HAR حقيقي بلا write methods ولا Authorization ولا Set-Cookie.
- لا يمنح runner أي صلاحية React write أو model/pilot/production.
