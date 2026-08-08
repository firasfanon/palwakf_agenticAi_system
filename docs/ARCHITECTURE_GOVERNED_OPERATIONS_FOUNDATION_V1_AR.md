# المعمارية — Governed Operations Foundation V1

```text
Operations UI (/operations)
         |
         v
/api/v1/governed-operations
  |--- task lifecycle engine
  |--- human review gateway
  |--- evidence lifecycle
  |--- local controls read model
         |
         v
audit/governed_operations.sqlite
  |--- governed_tasks
  |--- task_transition_events (hash chain)
  |--- human_reviews
  |--- evidence_records
  |--- schema_migrations
```

## دورة حياة المهمة

```text
draft → inbox → under_review → approved/rejected/returned → archived
```

- لا يحدث approve/reject/return إلا من `under_review`.
- لا يوجد انتقال إلى `executing`.
- كل مهمة تبقى `execution_state=NOT_EXECUTED`.
- كل انتقال يسجل actor وreason وevidence references وhash chain.

## الأدلة

الدليل لا يقرأ ملفًا ولا يستورد محتوى خارجيًا في V1. يحفظ Metadata فقط:
category, source_type, trust_level, raw_status, display_status, summary, source_reference, metadata, content_hash.

## التنفيذ

لا يوجد endpoint مثل `/execute` أو `/run` داخل Governed Operations. أي Future Execution Gateway يحتاج دفعة مستقلة وتفويضًا جديدًا.
