# عقد Read-Only ومصفوفة الاختبارات السلبية

## العقد الملزم

```text
HTTP_METHODS_FROM_REACT = GET_ONLY
FETCH_CREDENTIALS = OMIT
BROWSER_TOKEN_STORAGE = NONE
AUTHORIZATION_HEADER = NONE
REACT_WRITE_UI = NONE
BACKEND_ROUTE_MUTATION = NONE
SQLITE_MIGRATION = NONE
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NONE
COMMERCIAL_CLIENT_SCOPE_APPLY = NONE
PRODUCTION = BLOCKED
```

## المصفوفة

| الفحص | المتوقع في المرشح | النتيجة الساكنة |
|---|---|---|
| `fetch` | مسار واحد، `GET` و`credentials: omit` | PASS |
| أساليب الكتابة | لا `POST/PUT/PATCH/DELETE` ضمن React payload | PASS |
| اعتماد المتصفح | لا Bearer أو Authorization أو Cookie write | PASS |
| تخزين المتصفح | لا `localStorage/sessionStorage` | PASS |
| تنفيذ نموذج | لا UI أو API call لتشغيل Model | PASS |
| Pilot | لا زر/route write أو استدعاء تشغيل | PASS |
| SQLite | لا تغيير backend أو migration | PASS |
| العميل التجاري | لا UI لاختيار/حفظ client_id | PASS |
| React mount | المسارات القائمة فقط، لا FastAPI patch | PASS |

## حالات UX المقصودة

- **401/403:** تعرض الواجهة أن البيانات غير معروضة ولا تحاول تجاوز المنع.
- **خطأ الشبكة أو 5xx:** رسالة تشخيصية موجزة؛ لا بيانات وهمية ولا retry ينفذ جانبياً.
- **قائمة فارغة:** حالة فارغة صريحة، لا placeholder يبدو كسجل حقيقي.
- **مسار مقيد:** يشرح ما هو مقفل وسبب الحجب، من دون زر معطل غامض أو تنفيذ مخفي.

## ما لا تثبته هذه الحزمة

- لا تثبت Render في FastAPI الحقيقي على Windows.
- لا تثبت صحة بيانات backend الحالية أو صلاحياتها الفعلية.
- لا تثبت أي تفاعل مع Actor/Workspace/Client حقيقي.
- لا تثبت كتابة React أو عزل تجاري أو UAT إيجابي.
