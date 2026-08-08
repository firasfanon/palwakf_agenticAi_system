# Registry Bootstrap Contract V1.2

## Grounded target schema
The target registry uses the following properties for agent entries:

```text
agent_id
allowed_autonomy
runtime_enabled
runtime_mode
allowed_skills
forbidden_capabilities
```

No other registry properties are introduced by this closure.

## Required source state
- `registry_version=1.0`
- `execution_default=disabled`
- `coordinator` exists, enabled, `read_only_report_only`
- `sovereignty_reviewer` exists, enabled, `read_only_report_only`
- `knowledge_researcher` exists, disabled, `admission_required`
- `documentation_handoff` is absent

## Planned registry mutation
- Add exactly one `documentation_handoff` with `L0_READ_ONLY` only.
- Promote only `knowledge_researcher` from `admission_required` to `read_only_report_only`.
- Add `task_triage` to `sovereignty_reviewer`.
- Add `task_triage` and retain `evidence_assessment` for `knowledge_researcher`.
- Preserve existing forbidden capabilities for all existing agents.
- Preserve `execution_default=disabled`.

## Explicit non-goals
- No core runtime files are modified.
- No model call, platform access, database access, Git write, deployment, secret access, or memory write.
- No task generation runs automatically.
