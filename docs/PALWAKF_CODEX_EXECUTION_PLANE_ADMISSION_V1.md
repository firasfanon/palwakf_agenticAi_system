# PALWAKF CODEX EXECUTION PLANE ADMISSION V1

STATUS = IMPLEMENTATION_CANDIDATE
DATE = 2026-09-30
BASE_HEAD = 551372c297860023b8775cd38cb66f1cac4d4498

## Canonical role

CODEX_ROLE = PRIVILEGED_ENGINEERING_BOOTSTRAP_RECOVERY_PLANE

Codex does not replace PALWAKF_LOCAL_EXECUTOR and does not supersede PALWAKF_REMOTE_MCP.

- PALWAKF_LOCAL_EXECUTOR remains the governed operational execution plane.
- PALWAKF_REMOTE_MCP remains the secure bounded observability / diagnostics plane.
- REMOTE_DESKTOP_COMMANDER remains break-glass only.
- Render Responses relay and Task Scheduler relay are temporary migration mechanisms and are retired only after Codex bootstrap/recovery proof passes.

## Required execution mode

The admitted remote execution mode is SELF_HOSTED_CODEX_EXEC_SERVER.

Interactive Codex CLI login through a ChatGPT account is permitted for diagnostics and human-operated development, but it is not sufficient evidence for the autonomous remote execution plane.

Self-hosted exec-server admission requires:
1. Codex CLI installed on the authorized Windows device.
2. codex exec-server capability present.
3. Outbound connectivity to api.openai.com and codex-cloud-environments.chatgpt.com.
4. Application API credential held outside the executor environment.
5. A distinct restricted environment key passed to the executor as CODEX_API_KEY.
6. No API key, environment key, refresh token, or private credential committed to Git, Drive evidence, logs, or chat.
7. Exact repository-root allowlist and explicit governance boundaries.
8. Restart/reconnect proof before Render or Task Scheduler retirement.

## Allowed engineering roots

- C:\Users\DELL\StudioProjects\palwakf_workspace_manager
- C:\Users\DELL\StudioProjects\palwakf_mind_assistant
- C:\Users\DELL\StudioProjects\palwakf_agenticAi_system

Additional project roots require explicit admission.

## Governance boundaries

CODEX MUST NOT:
- bypass governed operational authority;
- mutate main without explicit authorization;
- promote a baseline without explicit authorization;
- mutate production or shared databases without explicit authorization;
- expose or log secret material;
- widen execution to arbitrary filesystem roots by default.

## Admission gates

GATE_C0_P3_PREDECESSOR = PASS
GATE_C1_SOURCE_AND_BOOTSTRAP = PENDING_RUNTIME
GATE_C2_CREDENTIAL_SEPARATION = PENDING
GATE_C3_SELF_HOSTED_CONNECTION = PENDING
GATE_C4_BOUNDED_READBACK = PENDING
GATE_C5_ENGINEERING_MUTATION_ON_TASK_BRANCH = PENDING
GATE_C6_RESTART_RECONNECT = PENDING
GATE_C7_ZERO_MANUAL_BOOTSTRAP_RECOVERY = PENDING
GATE_C8_RELAY_RETIREMENT_AUTHORIZATION = PENDING

## Credential separation

Application/API credential is used by the controller for Agents API session operations and model inference and remains outside the executor environment.
Executor environment credential is a restricted environment key passed to self-hosted exec-server as CODEX_API_KEY and must not be reused as the general application API key.

## Network contract

Required outbound destinations:
- https://api.openai.com
- wss://codex-cloud-environments.chatgpt.com

No inbound port is required for the self-hosted executor connection.

## Runtime evidence requirements

Admission evidence must record exact Codex version and path, exec-server availability, Windows identity, exact repo branch/head/tree, connection state, bounded readback, restart/reconnect, manual terminal intervention count, secret scan, and no main/baseline/production/shared-DB mutation.

## Retirement gate

Render Responses relay and Task Scheduler relay remain available until CODEX_SELF_HOSTED_CONNECT, CODEX_ENGINEERING_READBACK, CODEX_RESTART_RECONNECT, and CODEX_BOOTSTRAP_RECOVERY are all PASS.

References:
- https://developers.openai.com/api/docs/guides/agents-api/environments/self-hosted
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
