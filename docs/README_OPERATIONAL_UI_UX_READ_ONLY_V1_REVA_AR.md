# MEGA_BATCH_COMMAND_CENTER_OPERATIONAL_UI_UX_READ_ONLY_V1 — Rev A

## سبب Rev A
فشل Candidate السابق في Windows PowerShell 5.1 عند التحقق من نص عربي داخل سكربت PowerShell
مخزن UTF-8 بدون BOM. لم يكن الفشل في الواجهة أو في عقد القراءة.

## تصحيح Rev A
- تعتمد سكربتات التحقق على ASCII markers فقط.
- يضاف marker صريح:
  `READ_ONLY_OPERATIONAL_DASHBOARD`
- تبقى الواجهة عربية RTL كما هي.
- لا يتغير النطاق: 3 static assets فقط.
