# PALWAKF Local Agents — Model Output Contract Alignment Closure V1

## الغرض
إصلاح تعارض موثّق بين Prompt مشغّل القراءة فقط و`MODEL_OUTPUT_CONTRACT_V1`.

## النطاق
- مشروع `palwakf_local_agents` فقط.
- تحديث مقيّد لوحدة التحقق، عقد المخرجات، ومشغّل القراءة فقط.
- إضافة اختبار ساكن وEvals حتمية تمنع تكرار السبب.

## لا يشمل
- لا منصة PalWakf.
- لا SQL أو قاعدة بيانات.
- لا Git write أو نشر.
- لا ترقية صلاحيات أي Agent.
- لا اعتماد Memory أو Learning Candidate.
- لا إعادة تشغيل Ollama تلقائيًا.

## النتيجة المطلوبة قبل إعادة Pilot
1. تثبيت الدفعة.
2. نجاح `Test-ModelOutputContractAlignmentClosureV1.ps1`.
3. نجاح `Invoke-ModelOutputContractAlignmentEvalsV1.ps1`.
4. مراجعة بشرية للـPrompt الجديد.
5. إعادة تنفيذ Pilot واحد فقط يدويًا.
