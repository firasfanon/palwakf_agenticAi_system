# Command Center V1.2 Rev D — Static Gate Precision Hotfix

## الهدف
إصلاح محدود ودقيق لفحص Static Gate بعد أن أثبت Rev C أن ملف `__pycache__` لم يعد يُفحص، لكنه اعتبر
استدعاءات `.replace(...)` النصية ضمن `read_only_store.py` و`static/app.js` عمليات كتابة ملفات.

## السبب الجذري
`.replace(...)` قد تكون تطبيع نص أو مسار معروض أو صياغة واجهة. ليست عملية تعديل filesystem.
العملية الحساسة المقابلة هي `os.replace(...)`، وهي تبقى محظورة ومفحوصة بشكل صريح.

## التعديل
ملف واحد فقط:
`scripts/Test-CommandCenterV1RevBStatic.ps1`

الفحص الجديد:
- يستبعد `__pycache__` و`.pyc`.
- يعامل `.replace(...)` العامة كعملية نصية غير متحولة.
- يفحص عمليات filesystem في Python فقط: `write_text`, `write_bytes`, `unlink`, `rename`, `mkdir`, `rmdir`, `touch`, وعمليات `os`/`shutil` الحساسة.
- يفحص `app.js` ضد تعريف HTTP methods غير GET.
- لا يعدل FastAPI أو واجهة Command Center أو المهمة أو الـPilot.

## Evals مضافة
1. String `.replace()` في Python وJavaScript يجب أن يمر.
2. `Path(...).write_text(...)` يجب أن يُرفض.
3. `fetch(..., { method: "POST" })` يجب أن يُرفض.

## حدود السيادة
`MODEL_EXECUTION=NONE`
`PILOT_EXECUTION=NOT_EXECUTED`
`PLATFORM_MUTATION=NONE`
`DATABASE_ACCESS=NONE`
`GIT_WRITE=NONE`
`DEPLOYMENT=NONE`
`SECRETS_ACCESS=NONE`
`MEMORY_WRITE=NONE`
