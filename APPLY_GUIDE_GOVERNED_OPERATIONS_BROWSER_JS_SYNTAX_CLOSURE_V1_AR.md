# دليل التطبيق — Governed Operations Browser JS Syntax Closure V1

## الهدف
إغلاق عائق Browser Compile محصور في `governed_operations/static/app.js`.

## التغيير المسموح
استبدال literal newline غير صالح داخل `split(...)` بالتمثيل JavaScript الصحيح `\n`.

## نطاق التطبيق
- ملف هدف وحيد: `backend/src/palwakf_local_agents/governed_operations/static/app.js`
- لا تعديل لـ `app.py` أو routers أو stores أو Command Center أو SQLite أو API.

## السلامة
- `MODEL_EXECUTION=NONE`
- `PILOT_EXECUTION=NOT_EXECUTED`
- `LOCAL_SQLITE_WRITE=NONE`
- لا توجد مسارات `/execute` أو `/dispatch`.

## بوابات الإلزام
1. Candidate Syntax Gate: `node --check` للنسخة المرشحة.
2. Preflight: يفرض أن hash النسخة المستهدفة يساوي preimage المعروف.
3. Installer: يحفظ preimage وحيدًا ثم يطابق postimage ويفحصه بـ `node --check`.
4. Post-apply Static Gate: يعيد التحقق من hash، إزالة literal المعيب، وبقاء execution references محظورة.
