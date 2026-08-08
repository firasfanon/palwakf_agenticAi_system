# Local Agents Baseline Candidate — HAR Filename Reconciliation V1

```text
STATUS = PATCH_CANDIDATE_NOT_YET_APPLIED_ON_WINDOWS
SCOPE = EVIDENCE_RUNNER_ONLY
PREIMAGE_GUARD = REQUIRED
POSTAPPLY_STATIC_GATE = REQUIRED
```

بعد نجاح التطبيق والـStatic Gate، أضف إلى baseline أن Runner يدعم الاسم القياسي وملف HAR منفردًا محفوظًا باسم بديل، مع رفض الغموض.

تبقى القيود:

```text
NO_REACT_WRITE_CONTROL
NO_MODEL_EXECUTION
NO_PILOT
NO_DATABASE_ACCESS
NO_PLATFORM_MUTATION
NO_PRODUCTION_PROMOTION
```
