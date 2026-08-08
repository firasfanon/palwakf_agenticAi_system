# PALWAKF Local Agents — Dry Run Report Rendering Integrity Closure V1

## نبذة بالعربية
هذه الدفعة تصلح عيبين في تقرير الـDry Run فقط، بعد أن نجحت سلسلة المهمة ثم Evidence Gateway ثم Manifest ثم Context:

1. حقل `Security signals` ظهر فارغًا عند عدم وجود إشارات؛ يجب أن يظهر `NO_DETECTED_SECURITY_FLAG`.
2. علامات Markdown code fence في التقرير تحولت إلى نص مشوّه لأن PowerShell عالج backticks داخل Here-String مزدوجة.

## المعالجة
- تصفية قيم `security_flags` الفارغة أو null قبل قرار العرض.
- استعمال متغير `codeFence` بدل علامات backticks الحرفية داخل التقرير.
- لا تغيير على Evidence Gateway أو Runtime Module أو Contract أو Validator أو طلب Ollama.
- Installer ينفذ إصلاحًا مستهدفًا بسياق مطابق مع Backup للـRunner.

```text
MODEL_EXECUTION=NONE
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
```

## التحقق بعد التثبيت
1. اختبار عرض التقرير الساكن.
2. Dry Run واحد بدون `-Execute`.
3. مراجعة التقرير الجديد: Security signal يجب أن يكون `NO_DETECTED_SECURITY_FLAG`، وكتل النص تظهر بعلامات Markdown سليمة.
4. لا يُعاد تشغيل Ollama قبل اعتماد تقرير الـDry Run الجديد.
