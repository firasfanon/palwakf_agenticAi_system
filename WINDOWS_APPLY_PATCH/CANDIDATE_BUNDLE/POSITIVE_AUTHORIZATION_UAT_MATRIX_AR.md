# مصفوفة Controlled Positive Authorization UAT V1

| السطح | النطاق | Actor تجريبي | النتيجة الإيجابية المقبولة | محظورات ثابتة |
|---|---|---|---|---|
| Governed Operations | `palwakf_government` | `test_operator` | Task → Submit → Review → Evidence → Approve | model/pilot/platform/database execution |
| Local Agent Core | `palwakf_government` | `local.operator` | Preparation فقط | model/pilot execution |
| Capability Foundation | `research_learning` | `foundation.operator` | إنشاء Task محلي بعد تهيئة fixture فقط | commercial/client writes, pilot, external network |

## إثباتات إلزامية

- Actor ID المعلن يطابق Bearer principal في أسطح Legacy.
- جميع حالات النجاح تبقى `NOT_EXECUTED` أو `NONE` وفقًا للعقد.
- فرق الحالة بعد UAT لا يتجاوز ملفات SQLite/ledger المحددة في الاختبار المؤقت.
- لا ينشأ أي ملف في `commercial_projects` أو `personal_development`.

## استبعادات

لا يثبت هذا الاختبار وجود Actor production أو صلاحية React write أو صلاحية Commercial tenant أو Pilot execution.
