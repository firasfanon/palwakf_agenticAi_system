# MEGA_BATCH_LOCAL_AGENTS_CORE_AGENT_OPERATING_MODEL_AND_WORKSPACE_TASK_LIFECYCLE_CLOSURE_V1
## Analysis + Design Only — PalWakf Local Agents

**Authorization:** `AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_CORE_AGENT_OPERATING_MODEL_AND_WORKSPACE_TASK_LIFECYCLE_CLOSURE_V1_ANALYSIS_DESIGN_ONLY`  
**Timestamp UTC:** `2026-07-09T10:26:36.892772+00:00`  
**Reference baseline:** `LOCAL_AGENTS_SAFE_READ_MODEL_AND_OPERATIONAL_CONSOLE_R1_ACCEPTED_20260708`  
**Source archive:** `PALWAKF_LOCAL_AGENTS_FULL_SOURCE_BASELINE_20260709_124733.zip`  
**Source archive SHA-256:** `A86EB992B318F1DE65C73156F08B6881D686F52164428BE98373C4B153B82772`  

---

## 1) Nature of this batch

This is an **analysis/design-only closure**. It does not apply code changes.

```text
SOURCE_MUTATION = NONE
DATABASE_WRITE = NONE
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
PLATFORM_MUTATION = NONE
NETWORK = NONE
APPLY_AVAILABLE = FALSE
```

The objective is to refocus the product around the **Local Agents Core operating model** and define the contract needed before any future source-native candidate.

---

## 2) Governing strategic decision

The product center is:

```text
LOCAL_AGENTS_CORE = PRIMARY_PRODUCT_DIRECTION
EVIDENCE_LEDGER = SUPPORTING_GOVERNANCE_LAYER_ONLY
```

Evidence Ledger remains useful as a proof/audit layer, but it must not drive this stage.

---

## 3) Static source facts observed

### 3.1 Baseline archive

```text
ZIP_SHA256 = A86EB992B318F1DE65C73156F08B6881D686F52164428BE98373C4B153B82772
ZIP_ITEMS = 1213
SOURCE_FILES_CHECKED_FOR_SANDBOX_DRIFT = 1195
SANDBOX_STATIC_SOURCE_DRIFT = NONE
```

### 3.2 Existing registries / agent planes

The source currently has **three agent/registry planes**:

| Plane | Source | Current role |
|---|---|---|
| Role registry | `agents/registry_v2.yaml` | 14 strategic/specialist roles, all `L1_PLAN_ONLY`; 5 `admission_required_v2`, 9 `disabled_pending_admission`. |
| Runtime preparation registry | `backend/src/palwakf_local_agents/local_agent_core/registry.py` | 6 deterministic preparation agents with `model_execution=NONE`. |
| Command Center static registry | `backend/src/palwakf_local_agents/command_center/read_only_store.py` | Static read-only baseline entries for console display. |

**Design finding:** these planes are not wrong individually, but the product lacks a single read-model that explains their relationship. A future Candidate should not delete any plane; it should define a unifying projection.

### 3.3 Existing task planes

There are currently two task planes:

| Plane | Source | Current role |
|---|---|---|
| Command Center read-only queues | `tasks/inbox`, `tasks/approved`, `tasks/archived` via `command_center/read_only_store.py` | Read-only legacy/product dashboard projection. |
| Governed Operations workspace lifecycle | per-workspace `governed_operations.sqlite` via `governed_operations/store.py` | Formal lifecycle engine with transitions and review/evidence records. |

**Design finding:** future Local Agent outputs should bind to the governed task model by `workspace_id + task_id`, not only by objective text or evidence references.

### 3.4 Existing governed task lifecycle

Current lifecycle:

```text
draft → inbox → under_review → approved / rejected / returned → archived
```

Current transitions:

```json
{
  "draft": [
    "inbox",
    "archived"
  ],
  "inbox": [
    "under_review",
    "archived"
  ],
  "under_review": [
    "approved",
    "rejected",
    "returned"
  ],
  "returned": [
    "inbox",
    "archived"
  ],
  "approved": [
    "archived"
  ],
  "rejected": [
    "archived"
  ],
  "archived": []
}
```

Design constraint: **approval remains a governance state, not execution permission**.

### 3.5 Existing UI posture

React console currently reads only through `useRead` paths:

```text
- /api/v1/governed-operations/workspaces
- /api/v1/local-agent-core/agents
- /api/v1/local-agent-core/workspaces/palwakf_government/model-pilot/status
- /api/v1/local-agents/dashboard
- /api/v1/local-agents/evidence
- /api/v1/local-agents/reviews
- /api/v1/local-agents/tasks
- /api/v1/workspaces
- /health
```

The browser client sends only GET requests and omits credentials in `frontend/src/api/client.ts`.

**Design constraint:** no React write controls should be introduced until server-side actor/workspace authorization is unified and proven.

### 3.6 Existing authorization posture

`config/local_actor_scope_registry_v1.json` is configured as:

```text
CONTRACT = LOCAL_ACTOR_SCOPE_REGISTRY_V1
DEFAULT_ACCESS = DENY
ACTOR_COUNT = 0
```

Design implication: backend write/preparation routes can exist as governed surfaces, but no real local actor is provisioned by this batch. Product UI must stay read-only.

### 3.7 Pilot/model posture

There are multiple pilot-related surfaces/configurations, but current batch does not reconcile or execute them.

```text
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
PILOT_RECONCILIATION = OUT_OF_SCOPE
```

A later dedicated Pilot Gate batch is required before using any model route.

---

## 4) Core operating model

### 4.1 Canonical concepts

| Concept | Definition |
|---|---|
| `Workspace` | Sovereign operational boundary; controls policy pack, storage scope, actor scope, and cross-workspace denial. |
| `AgentRole` | Human/strategic role from `registry_v2`; describes responsibilities, skills, limits, and admission status. |
| `AgentRuntimeProfile` | Backend deterministic preparation profile; can produce reviewable output but not execute actions. |
| `Task` | Governed unit of work inside a workspace. |
| `AgentAssignment` | Binding of `workspace_id + task_id + agent_role_id + optional runtime_profile_id`. |
| `AgentPreparation` | Reviewable generated/derived package; must persist `execution_state=NOT_EXECUTED`. |
| `ReviewPacket` | Human review object containing decision prompts, risk flags, policy controls, and evidence references. |
| `ActionProposal` | A non-executing proposal. It can be accepted as planning output, but it cannot mutate source/system without a separate Apply authorization. |

### 4.2 Agent autonomy ceiling

| Level | Meaning | Current status |
|---|---|---|
| `L0_READ_ONLY` | View safe read-model data only. | Allowed in console. |
| `L1_PLAN_ONLY` | Produce plans, classifications, triage notes. | Current strategic ceiling. |
| `L2_DETERMINISTIC_PREPARE_ONLY` | Deterministic local preparation with human input. | Backend core exists, but UI write use remains blocked. |
| `L3_MODEL_DRAFT_PILOT_GATED` | Model draft only under separate pilot. | Blocked. |
| `L4_ACTION_PROPOSAL_ONLY` | Proposal for future action, not execution. | Design target. |
| `L5_EXECUTION` | Actual execution/mutation. | Forbidden in current roadmap. |

---

## 5) Proposed lifecycle overlay

This batch should not replace the current governed task lifecycle. It should add a conceptual overlay for agent work:

```text
agent_not_requested
→ agent_suggested
→ agent_preparation_requested
→ prepared_for_human_review
→ human_review_accepted / human_review_returned / human_review_rejected
→ archived
```

Hard invariant:

```text
ALL_AGENT_OUTPUT_STATES.execution_state = NOT_EXECUTED
ALL_AGENT_OUTPUT_STATES.model_execution = NONE unless separate Pilot authorization exists
ALL_AGENT_OUTPUT_STATES.platform_mutation = NONE
```

Mapping to task lifecycle:

| Governed task state | Agent overlay allowed? | Notes |
|---|---|---|
| `draft` | suggest / prepare plan only | No execution. |
| `inbox` | triage / select role / prepare review packet | No execution. |
| `under_review` | reviewer evaluates output | Only review decision. |
| `approved` | governance acceptance only | Does not imply Apply. |
| `returned` | rework preparation | No execution. |
| `rejected` | stop or archive | No execution. |
| `archived` | read-only historical display | No execution. |

---

## 6) Required unification contract for next Candidate

A future source-native candidate should introduce or validate a **read-only unifying contract**, not a write-heavy implementation.

### 6.1 Registry unification

Create a projection such as:

```text
UnifiedAgentCard {
  agent_role_id
  title_ar
  admission_status
  autonomy_ceiling
  allowed_skills
  prohibited_actions
  runtime_profile_ids[]
  workspace_admission[]
  output_mode
}
```

Rules:

```text
registry_v2.yaml remains the strategic role source.
local_agent_core/registry.py remains deterministic runtime profile source.
command_center static registry must not become canonical after this stage.
```

### 6.2 Task binding

Future `AgentPreparation` should formally bind to:

```text
workspace_id
task_id
agent_role_id
runtime_profile_id
preparation_id
review_packet_id
```

If `task_id` is absent, the output remains an unbound planning artifact and must not appear as task-specific work.

### 6.3 Human Review Gate

A review packet must state:

```text
- what the agent proposed
- which workspace and task it relates to
- why it is allowed
- prohibited actions that remain blocked
- whether evidence is cited
- approval effect = NO_EXECUTION_AUTHORITY_GRANTED
```

### 6.4 Action proposal boundary

`approved` means:

```text
APPROVED_AS_PLANNING_OUTPUT
```

It must not mean:

```text
APPROVED_TO_EXECUTE
APPROVED_TO_APPLY
APPROVED_TO_DEPLOY
APPROVED_TO_WRITE_DB
```

---

## 7) UI implications

Current `/agent-console` should evolve as a read-only operations cockpit:

1. **Agent Cards**  
   Show unified role + runtime readiness + workspace eligibility.

2. **Task Detail**  
   Show suggested/assigned agent, preparation state, and review packet state.

3. **Review Packet Panel**  
   Show decision prompts and blocked actions.

4. **Tools Page**  
   Keep deterministic tools as read-only/prepare-only until an explicit actor provisioning and write-control batch exists.

5. **Pilot Control**  
   Stay blocked and transparent.

No buttons for Run / Execute / Apply / Deploy / Git / Shell should appear.

---

## 8) Security invariants

```text
NO_AGENT_EXECUTION
NO_MODEL_EXECUTION_BY_DEFAULT
NO_PILOT_EXECUTION
NO_DB_WRITE
NO_PLATFORM_MUTATION
NO_GIT_WRITE
NO_SHELL_EXECUTION_THROUGH_PRODUCT
NO_EXTERNAL_NETWORK
NO_CROSS_WORKSPACE_ACCESS
NO_REACT_WRITE_CONTROL
NO_EVIDENCE_LEDGER_EXPANSION_IN_THIS_BATCH
```

Additional invariants:

```text
workspace_id comes from route / trusted context, not arbitrary body reassignment.
actor registry remains default-deny until a separate actor provisioning workflow.
commercial client context remains mandatory for commercial workspace writes.
preparation output cannot self-promote to memory or baseline.
```

---

## 9) Acceptance criteria for the next Candidate-only batch

A future Candidate should pass only if it proves:

```text
CANDIDATE_COPY_ISOLATED = TRUE
LIVE_SOURCE_BACKEND_IMPORT = FORBIDDEN
SOURCE_PREIMAGE_WRITTEN = TRUE
SOURCE_POSTIMAGE_WRITTEN_IN_FINALLY = TRUE
SOURCE_UNCHANGED_ON_FAILURE = TRUE

UNIFIED_AGENT_CARD_CONTRACT = PASS
TASK_ID_BINDING_CONTRACT = PASS
HUMAN_REVIEW_PACKET_NO_EXECUTION_AUTHORITY = PASS
ACTION_PROPOSAL_NOT_EXECUTION = PASS
FRONTEND_GET_ONLY_CONTRACT = PASS
NO_MODEL_OR_PILOT_EXECUTION = PASS
NO_EVIDENCE_LEDGER_SCOPE_EXPANSION = PASS
```

No Apply should be produced by that Candidate unless separately authorized after human review.

---

## 10) Decision

```text
RESULT = PASS
DECISION = DESIGN_READY_FOR_HUMAN_REVIEW_NO_APPLY
SOURCE_BASELINE = UNCHANGED
NEXT_STEP = SOURCE_NATIVE_CANDIDATE_ONLY_AFTER_EXPLICIT_AUTHORIZATION
```

Suggested next authorization:

```text
AUTHORIZE_MEGA_BATCH_LOCAL_AGENTS_CORE_AGENT_OPERATING_MODEL_AND_WORKSPACE_TASK_LIFECYCLE_CLOSURE_V1_SOURCE_NATIVE_CANDIDATE_ONLY
```
