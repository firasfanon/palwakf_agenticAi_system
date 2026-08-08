# Changelog — Windows UAT Runner Path Resolution Repair V2

- أصلح default parameter evaluation المعتمد على `$PSScriptRoot` في Runner وStatic Gate.
- أصلح Recovery Patch نفسه بتجنب `$PSScriptRoot` داخل `param`.
- أضيف Parser Gate لكلا الملفين قبل وبعد التطبيق.
- لا تغييرات على المصدر التشغيلي أو React أو FastAPI.
