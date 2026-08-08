# PALWAKF Local Agents — Evidence Gateway Dependency Restoration Merge Closure V1

## نبذة بالعربية
هذه الدفعة تصلح خطأ دمج ظهر بعد دفعة Exact Output Boundary: تم استبدال الـRuntime Module وإسقاط الدالة `New-ReferenceEvidenceManifest` التي يعتمد عليها Evidence Gateway. لذلك توقّف الـPilot قبل بناء Manifest وقبل استدعاء Ollama.

تستعيد الدفعة دوال بناء Evidence Manifest، وتحافظ في الوقت نفسه على عقد 13 سطرًا وحدود `OUTPUT_CONTRACT_START` و`OUTPUT_CONTRACT_END` ورفض النص اللاحق.

## ما تتضمنه الدفعة
- Runtime Module مدمج يجمع وظائف Evidence Gateway مع Exact Output Validator.
- Gateway يعيد فحص توفر `New-ReferenceEvidenceManifest`.
- Runner مقيد يعيد فحص Registry وSkill Assignment وPrompt Injection قبل التنفيذ.
- اختبار Dependency Restoration يثبت أن الدالة محدثة ومصدّرة وأن Manifest Probe ينجح في الذاكرة فقط.
- Exact Output Evals وBaseline Read-only Evals.
- Installer ينشئ Backup محليًا قبل الاستبدال.
- Restore Script للعودة إلى Backup محدد.

## لا يتغير
```text
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MODEL_EXECUTION=DISABLED_BY_DEFAULT
```

## التحقق بعد التثبيت
لا تشغل `-Execute` للنموذج قبل نجاح الاختبارات الأربعة التالية:
1. Dependency Restoration Test
2. Exact Output Static Test
3. Exact Output Evals
4. Baseline Read-only Evals

ثم تنفذ Gateway فقط، دون `-Execute`، للتأكد من إنشاء Manifest.
