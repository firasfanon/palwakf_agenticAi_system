# Tool Gateway and Model Routing V2

## Tool policy
Every tool call must have:
- an assigned role,
- a task ID,
- an allowed skill,
- an approved scope,
- an audit record,
- a result classified for sensitivity.

## Current V2 tool state
| Tool group | State |
|---|---|
| Read project-approved documents | contractual only; runner not yet enabled |
| File inventory / static trace | contractual only; runner not yet enabled |
| Local report write | contractual only; runner not yet enabled |
| Git write | prohibited |
| SQL/DB | prohibited |
| Browser automation | prohibited |
| Network write | prohibited |
| Deployment | prohibited |
| Secrets read | prohibited |

## Model routing
- Small local model: classification, closed-contract extraction, Arabic template rendering.
- Stronger reasoning model: complex analysis, only after separate policy and evaluation.
- Deterministic validator: schema, allowlist, evidence completeness, pass/fail.
Model name never substitutes for evidence.
