# Error Record — Product Start Screen Candidate

| المعرّف | السبب | الملفات | ما فشل | المعالجة | آخر baseline مستقر |
|---|---|---|---|---|---|
| `E-20260706-01` | مرر مكوّن `StateGate` Function Child داخل Fragment بدل تمريره مباشرة. | `PATCH_PAYLOAD/frontend/src/App.tsx` | أول `tsc --noEmit` أعاد `TS2322` و`TS7006`. | أزيل Fragment وأصبح child دالة صحيحة. أعيد `tsc` ونجح. | `WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED` |
| `E-20260706-02` | بيئة العرض المعزولة حجبت Browser headless من الوصول إلى `127.0.0.1`، ولم تنتج Runtime screenshot معتمدًا. | بيئة المعاينة فقط، لا ملف مشروع | محاولة render الحي لم تكن صالحة كدليل runtime. | أُنتجت صور **source-derived / mock only**، وجرى فصل Windows Runtime UAT في Runbook مستقل. | `WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED` |

لا توجد أخطاء متبقية تمنع صحة TypeScript أو build للمرشح. لا يزال Runtime/UAT غير منفذ عن قصد.
