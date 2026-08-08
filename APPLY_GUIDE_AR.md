# دليل تطبيق LOCAL_AGENT_READ_ONLY_PILOT_LIFECYCLE_CLOSURE_V1.2 Rev C

## الترتيب الإلزامي
1. Package Syntax Gate.
2. SAPF Static Gate + SAPF Evals + Pack 01 recheck.
3. Candidate Preflight.
4. Installer `-WhatIf` فقط.
5. لا تطبق قبل تفويض صريح منفصل.
6. بعد Apply: Static Test + Deterministic Evals + regression checks.
7. بعد إغلاق الحزمة فقط: Human Review Decision، ثم Archive، ثم Active State Check.

## إصلاح Rev C
- Rev B لا يطبق: سجلت مهلة 90 ثانية للـEvals مع `stdout/stderr` فارغين.
- السبب الجذري: `Copy-Item` كان ينسخ `$tempRoot` إلى `Join-Path $tempRoot 'bad'`؛ أي إلى descendant من المصدر، فينشأ تكرار `bad\bad\...`.
- Rev C ينسخ محتويات fixture إلى sibling temp root مستقل، ويمنع برمجيًا أي destination أسفل `$tempRoot`.
- مخرجات `EVAL_STAGE` لا تعني تشغيل نموذج؛ هي علامات تقدم تشخيصية فقط.

لا يوجد Model Execution أو Task Generation أو Platform/DB/Git/Deployment/Secrets/Memory scope في هذه الدفعة.
