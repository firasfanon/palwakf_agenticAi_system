# PALWAKF Local Agents — Exact Output Boundary and Trailing Text Closure V1

## نبذة بالعربية
هذه الدفعة تعالج حالة ظهرت في Pilot القراءة فقط: النموذج التزم بالمفاتيح المطلوبة، لكنه أضاف نصًا بعد المخرجات الصارمة. لا يتم تخفيف الـValidator؛ بل يصبح السياق أكثر انضباطًا، مع بداية ونهاية صريحتين وتشخيص دقيق للنص اللاحق.

## ما يتغير
- Contract يتطلب `OUTPUT_CONTRACT_START` و`OUTPUT_CONTRACT_END`.
- المخرجات الصحيحة تحتوي 13 سطرًا بالضبط.
- أي نص بعد النهاية يرفض، مع hash تشخيصي.
- الـPrompt ينتهي بقفل مخرجات صريح بعد كل الأدلة.
- لا يسمح بتكرار paths أو snippets أو محتوى مرجعي في المخرجات.
- يظل التنفيذ معطّلًا افتراضيًا، ولا يعمل Ollama إلا مع `-Execute`.

## ما لا يتغير
- PLATFORM_MUTATION=NONE
- DATABASE_ACCESS=NONE
- GIT_WRITE=NONE
- DEPLOYMENT=NONE
- SECRETS_ACCESS=NONE
- HUMAN_APPROVAL_REQUIRED=YES

## الترتيب المطلوب
1. نفذ `-WhatIf`.
2. نفذ التثبيت بعد المراجعة.
3. شغّل static test وdeterministic evals فقط.
4. راجع النتائج.
5. لا تستخدم `-Execute` قبل قبول التحقق الساكن والـevals.
