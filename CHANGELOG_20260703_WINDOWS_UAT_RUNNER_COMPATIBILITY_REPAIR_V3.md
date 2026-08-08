# Changelog — Windows UAT Runner Compatibility Repair V3

- أضيف إصلاح V3 محدود لأدوات Windows Local Browser UAT.
- استبدال defaults المعتمدة على `$PSScriptRoot` داخل `param` بحل متأخر للمسار.
- إصلاح عدّ أخطاء Parser ليكون آمنا تحت Windows PowerShell 5.1 و`Set-StrictMode`.
- تضمين `PATCH_PAYLOAD` كاملًا داخل الحزمة.
- لا تغيير لتطبيق React/FastAPI أو عقود read-only أو الإنتاج.
