# معمارية النطاق

```text
/workspaces/<workspace_id>/governed_operations.sqlite
  ├─ governed_tasks
  ├─ task_transition_events
  ├─ human_reviews
  ├─ evidence_records
  └─ audit_events

workspace_core registry + policy pack
  → policy/agent permission intersection
  → local lifecycle only
```

العزل **مادي ومنطقي**: المعرف يأتي من مسار API، لا من body، والتحقق يرفض أي حقل `workspace_id` زائد. المهمة المولدة في مساحة لا تكون قابلة للقراءة من مساحة أخرى.
