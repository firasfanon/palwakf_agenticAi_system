# Candidate Repair Notice — Governed Local Agent Core V1

## Status

This package supersedes the original `PALWAKF_LOCAL_AGENTS_MEGA_BATCH_GOVERNED_LOCAL_AGENT_CORE_V1_CANDIDATE` for Candidate Syntax, Preflight, WhatIf, and any future Apply.

## Repair scope

No project source file under `backend/**` was changed. The repair is package-side only:

- `scripts/Test-GovernedLocalAgentCoreV1Preflight.ps1`
  - Replaced invalid PowerShell statement-as-expression forms with subexpressions: `$()`.
- `scripts/Test-GovernedLocalAgentCoreV1CandidateSyntax.ps1`
  - Added static guards for the invalid expression forms.
  - Added a temporary-fixture runtime smoke test proving the Preflight script reaches `PREFLIGHT_RESULT=PASS`.

## Security and mutation boundary

- Project mutation: none during Candidate Syntax or Preflight.
- Smoke fixture and evidence are created only under `%TEMP%` and removed by the Candidate Syntax script.
- Backend postimage source hashes remain identical to the original V1 candidate.
- The governed local agent core design, routes, policies, SQLite boundary, model-runtime disablement, and execution prohibitions are unchanged.
