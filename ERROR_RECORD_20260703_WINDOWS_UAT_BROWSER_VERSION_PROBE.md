# Error Record — Browser Version Probe False Failure

- التاريخ: 2026-07-03
- المرحلة: `BROWSER_DISCOVERY`
- الدليل: `msedge.exe` موجود، و`--version` أعاد `exit=0` بلا مخرجات.
- السبب: Runner V4 اشترط مخرجات نصية غير فارغة مع أن Edge المُدار قد لا يطبعها في هذا السياق.
- المعالجة: V5 يقبل خروج `0` ويستخرج `ProductVersion`/`FileVersion` عند توفره. فشل تشغيل Headless أو Capture لم يُخفف.
- آخر baseline مستقر: React lock/build/http UAT baseline + أدوات Windows UAT قبل إتمام Browser-rendered UAT.
