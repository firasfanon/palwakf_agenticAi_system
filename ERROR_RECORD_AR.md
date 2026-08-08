# Error Record — Read-Only Frontend Visual Inspection

| الحقل | القيمة |
|---|---|
| المعرف | `LOCAL_AGENTS_FRONTEND_VISUAL_RENDER_ENVIRONMENT_LIMITATION_20260706` |
| السبب | سياسة متصفح داخل بيئة التحليل حجبت التنقل إلى `http://127.0.0.1` و`file://` برسالة `ERR_BLOCKED_BY_ADMINISTRATOR`. |
| الملفات المتأثرة | لا يوجد ملف من المشروع متأثر. |
| ما فشل | إنتاج Runtime Screenshot مباشر من Chromium داخل بيئة التحليل. |
| ما لم يفشل | استخراج React source، فحص CSS/routes/API contract، وإنتاج معاينة مصدرية من `frontend/dist`. |
| الحل | تشغيل `Invoke-WindowsLocalBrowserUatAndRuntimeEvidenceV1.ps1` محليًا على Windows داخل Worktree معزول للحصول على PNG/DOM/HAR حقيقي. |
| آخر baseline مستقر | `WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED` |

هذا القيد لا يبرر أي تجاوز لأمن المتصفح أو أي تبديل لحدود المشروع.
