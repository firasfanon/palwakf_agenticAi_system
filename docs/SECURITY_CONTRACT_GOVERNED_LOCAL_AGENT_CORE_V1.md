# Security Contract

- workspace_id comes only from the route and is server-validated.
- Pydantic forbids injected workspace_id in request bodies.
- Each workspace has a distinct `workspaces/<workspace_id>/local_agent_core.sqlite` only after an explicit human preparation request.
- Cross-workspace reads return not found because the lookup runs against the addressed workspace database only.
- No route named execute, dispatch, model, shell, git, deploy, or database-write is exposed.
- `execution_state=NOT_EXECUTED`, `model_execution=NONE`, and `pilot_execution=NOT_EXECUTED` are persisted in every preparation.
- Human review packet does not grant execution authority.
