
# Browser UAT

1. شغّل الخادم محليًا وافتح `/command-center` مع DevTools Network.
2. أعد التحميل مع Disable cache.
3. تنقّل 15 مرة على الأقل بين Dashboard, Tasks, Reviews, Evidence, Agents, Governance, System Health.
4. تأكد أن عدد طلبات `system-health` يزداد بقدر التنقل/التحديث فقط، وليس بمضاعفات متزايدة.
5. تأكد من غياب `ERR_INSUFFICIENT_RESOURCES` و`Throttling navigation`.
6. أرسل لقطة Network بعد الاختبار.

حد القبول: لا أكثر من طلب system-health واحد لكل render مقصود، ولا طلبات تنفيذ أو كتابة.
