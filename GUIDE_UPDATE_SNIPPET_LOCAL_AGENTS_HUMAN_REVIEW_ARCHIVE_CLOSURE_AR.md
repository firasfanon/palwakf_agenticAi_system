# مقتطف تحديث الدليل الحاكم — Local Agents

أضيف إلى ملف الدليل الحاكم الخاص بالمساعدين المحليين:

```text
بعد أي Pilot منفذ: لا تعتبر حالة ملف Task وحدها مصدر الحقيقة.
يجب مطابقة TaskId مع Raw/Canonical/Report/Evidence Manifest.
إذا ثبت التنفيذ وبقيت المهمة Approved أو Running، لا تعدل JSON يدويًا.
يجب أولًا إنشاء Human Review Decision محدود النطاق، ثم Archive عبر المسار المعتمد، ثم Test-ReadOnlyPilotActiveStateV1.ps1.
لا يمكن النظر في Pilot جديد قبل ACTIVE_TASK_COUNT=0 وACTIVE_PILOT_STATE=PASS.
```
