# تسلسل التنفيذ بعد Baseline

1. قبول baseline: تثبيت static roots، hashes، API contract inventory، وframework state.
2. إعداد Apply Candidate كامل للواجهة بناءً على hashes الفعلية فقط.
3. Syntax + Preflight + WhatIf.
4. Apply مستقل بتفويض جديد.
5. Browser UAT: desktop، mobile، RTL، loading/error/denied، client boundary.
6. بعد الإغلاق: الانتقال إلى Vertical Slices Full Stack بدلاً من Backend-first.

## Vertical Slice rule
كل قدرة لاحقة يجب أن تشمل معاً:

`UI + API contract + actor scope + client scope + audit/evidence + UAT`
