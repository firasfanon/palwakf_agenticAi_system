# دليل تشغيل مختصر

1. فك/ضع المصدر المطبق في مساره المحلي.
2. افتح PowerShell داخل جذر المشروع.
3. شغّل فحص الحزمة:
   ```powershell
   .\scripts\Test-WindowsLocalBrowserUatAndRuntimeEvidenceV1Static.ps1
   ```
4. شغّل UAT دون Registry افتراضيًا:
   ```powershell
   .\scripts\Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1 -DependencyMode OfflineCache
   ```
5. أثناء التشغيل، صدّر HAR إلى المسار المعروض وأغلق نافذة المتصفح.
6. أرسل ملف archive الناتج وملف SHA-256 للمراجعة.

لا تستخدم حسابًا إداريًا، ولا تعدّل إعدادات Browser policies، ولا تنقل bind من `127.0.0.1`.
