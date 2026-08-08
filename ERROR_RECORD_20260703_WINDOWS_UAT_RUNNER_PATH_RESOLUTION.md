# Error Record — Windows UAT Runner Path Resolution

## الخطأ

`Join-Path` / `Split-Path` رفضا قيمة Path الفارغة داخل Runner وStatic Gate وRecovery Patch.

## السبب الجذري

اعتمدت قيم `param` الافتراضية على `$PSScriptRoot`. في Windows PowerShell 5.1 لا يجوز الاعتماد على هذا المتغير داخل default parameter expression لأن هذه التعبيرات تُقيّم قبل تهيئة مسار السكربت.

## الأثر

لا يبدأ أي UAT أو Build أو خدمة؛ الفشل يحدث أثناء parameter binding.

## العلاج V2

- جعل `ProjectRoot` و`PayloadRoot` فارغين افتراضيًا.
- حل مسار السكربت بعد `param` باستخدام `$PSCommandPath` ثم `$MyInvocation.MyCommand.Path` كبديل.
- فحص PowerShell Parser لكل من runner وstatic gate في payload وفي target بعد النسخ.
- إنشاء backup تلقائي واسترجاع عند أي فشل.

## آخر Baseline مستقر

`PALWAKF_LOCAL_AGENTS_WINDOWS_LOCAL_BROWSER_UAT_RUNTIME_EVIDENCE_APPLIED_SOURCE_20260703.zip`
