# Session Handoff — Legacy Write Authorization Closure V1

## نقطة الاستئناف

التسليم الحالي يضيف Boundary خادمي fail-closed لمسارات Legacy ويثبت Negative UAT في نسخة مصدر معزولة. لا يثبت بعد أن كل suite قديم متوافق مع العقد الجديد، ولا يفتح React write.

## ما طُبق

- ستة ملفات سلوك خادمي من الـCandidate.
- ملف Negative UAT مصحح منهجيًا.
- ثلاثة scripts جديدة: Static Gate، Negative UAT Runner، Rollback؛ إضافة إلى Apply خارجي موقّع hash-wise.

## ما اجتاز

- preimage hashes: PASS في النسخة المعزولة.
- postimage hashes: PASS.
- Python static compile: PASS.
- route count: 15.
- Negative UAT: 25 passed.

## ما بقي

1. تحديث 15 اختبارًا Legacy لتضمين actor/token fixtures ومسارات workspace الصحيحة، وفصل marker UI المستقل.
2. تنفيذ Positive Authorization UAT محدود باستخدام actors اختبارية قابلة للإزالة، بدون React UI write وبدون Pilot/Model execution.
3. إعادة Full Backend Suite حتى PASS قبل أي مناقشة لتفويض React write.
4. لاحقًا فقط: review لتصميم `client_id` persistence في `governed_operations` و`local_agent_core`؛ حاليًا commercial legacy write يبقى denied.

## أوامر Windows بعد مراجعة الحزمة

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Apply-LegacyWriteAuthorizationClosureV1.ps1" -ProjectRoot (Get-Location).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\Test-LegacyWriteAuthorizationClosureV1Static.ps1" -ProjectRoot (Get-Location).Path
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\Run-LegacyWriteAuthorizationNegativeUatV1.ps1" -ProjectRoot (Get-Location).Path
```

## Rollback

استخدم المسار الذي يظهر في `BACKUP_ROOT=`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\Rollback-LegacyWriteAuthorizationClosureV1.ps1" -ProjectRoot (Get-Location).Path -BackupRoot "<BACKUP_ROOT>"
```
