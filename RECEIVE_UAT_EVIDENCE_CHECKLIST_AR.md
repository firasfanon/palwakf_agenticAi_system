# ملف الاستلام بعد تشغيل Windows UAT

ارفع **مجلد Output الناتج كاملًا كملف ZIP واحد** دون حذف أو تعديل، وبالأخص:

```text
UAT_EXECUTION_STATUS.json
BROWSER/BROWSER_UAT_REPORT.json
BROWSER/NETWORK_SUMMARY.json
BROWSER/CONSOLE.json
BROWSER/*.png
BROWSER/*.html
BACKEND_STDOUT.log
BACKEND_STDERR.log
NPM_CI_OFFLINE.log
TSC_NO_EMIT.log
VITE_BUILD.log
```

## لا ترفع

- `.env` أو مفاتيح API أو Tokens.
- قاعدة SQLite أو نسخ من بيانات العملاء.
- `node_modules` أو Edge Profile إذا احتوى بيانات شخصية غير لازمة.

## قاعدة التحكيم

لا يكفي ظهور تطبيق في المتصفح. يجب أن يحتوي `BROWSER_UAT_REPORT.json` على:

```text
result = WINDOWS_RUNTIME_UAT_PASS
GET_ONLY_NETWORK = PASS
CREDENTIALS_OMIT_OBSERVED = PASS
NO_REACT_WRITE = PASS
CONSOLE_ERRORS = PASS
```
