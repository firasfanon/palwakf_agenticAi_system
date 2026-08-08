# Validation Report — Candidate Construction

## Static checks performed during construction
- Python AST parse performed for each candidate Python source file.
- Configuration contract verified: `enabled=false`, provider `ollama_local_only`, external network `NONE`.
- Package inventory and SHA-256 manifest generated.
- Candidate unit tests were executed in a simulated target built from the accepted Workspace Core and Agent Core V1 postimages: `11 passed`.
- No Ollama endpoint was contacted during candidate validation.

## Important limitation
This candidate was assembled against the accepted Governed Local Agent Core V1 source postimage. The target machine must run package Syntax, Preflight, and WhatIf before any Apply decision.
