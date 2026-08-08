# Error Record — UAT Harness Reconciliation (2026-07-07)

## المعرف

`LOCAL_AGENTS_PRODUCT_CONSOLE_APPLY_STATIC_GATE_SEQUENCE_MISMATCH_V1`

## السبب الجذري

سكربت `Invoke-ProductConsoleReadOnlyApplyV1.ps1` ينسخ Payload إلى الـworktree أولًا، ثم يستدعي `Test-ProductConsoleReadOnlyCandidateStaticGate.ps1`. الأخير يفحص `PREIMAGE_SHA256.json` على مسار الـworktree. للملفات التي تغيرت فعلًا (`App.tsx` و`client.ts` و`Layout.tsx` و`styles.css`) لا يمكن لها بعد النسخ أن تطابق Preimage؛ ينبغي أن تطابق Postimage.

## الملفات المعنية

- `scripts/Invoke-ProductConsoleReadOnlyApplyV1.ps1`
- `scripts/Test-ProductConsoleReadOnlyCandidateStaticGate.ps1`
- `PREIMAGE_SHA256.json`
- `POSTIMAGE_SHA256.json`

## ما فشل منطقيًا

لا يمكن اعتماد `STATIC_GATE_PASS` الناتج عن هذا التسلسل باعتباره قابلاً لإعادة التنفيذ من السكربتين كما هما، حتى لو وُجد تقرير مخرجات سابق يدعي النجاح.

## الحل في هذه الحزمة

لا تُعدّل هذه الحزمة المصدر أو الـcandidate. تتحقق من الـ`POSTIMAGE_SHA256.json` فقط قبل Runtime UAT؛ أي الحالة الصحيحة لمساحة عمل تم تطبيق المرشح فيها. أما إصلاح سكربت Apply نفسه فيلزم تفويض حوكمة/patch منفصل لاحقًا.

## آخر baseline مستقر

```text
WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED
```

## الأثر على القرار الحالي

`WINDOWS_RUNTIME_UAT` لا يعتبر منفذًا بعد. هذه الحزمة تجهز مسارًا قابلًا للتنفيذ على Windows لإنتاج الدليل الحقيقي.
