# عقد الأرشيف الدائم للأدلة — V1

## الغرض

استبدال الاعتماد الحصري على `%TEMP%` بأرشيف دائم خاضع للتتبع والاحتفاظ.

## البنية المقترحة

```text
evidence/accepted/
  YYYY/
    YYYYMMDD/
      <immutable-evidence-id>/
        manifest.json
        SHA256SUMS.txt
        review-decision.json
        artifacts/
```

## الحقول الدنيا في `manifest.json`

```text
evidence_id
timestamp_utc
producer
scope
workspace_id
actor_id
client_id_when_applicable
operation
artifact_hashes
candidate_hash
baseline_hash
review_decision
retention_class
source_location
```

## قواعد

```text
APPEND_ONLY
NO_OVERWRITE
SHA256_REQUIRED
HUMAN_REVIEW_DECISION_LINK_REQUIRED_WHEN_POLICY_DEMANDS
NO_SECRET_MATERIAL
NO_UNAPPROVED_MODEL_OUTPUT_AS_ACCEPTED_EVIDENCE
```

## ما لم يتم

لم يُنشأ أي مسار أرشيف ولم تُنقل أدلة من `%TEMP%` ضمن هذه الحزمة.
