# Static Validation Scope Contract V1.3

## Root cause closed
The prior V1.2 static test scanned every `scripts/*.ps1` file in the local project and treated every `$name:` token as potentially unsafe interpolation. This incorrectly flagged legitimate PowerShell scope-qualified variables such as `$script:` and `$env:` in scripts that are outside Pack 01.

## V1.3 validation rule
The Pack 01 static validator checks:
1. Registry state for the four Pack 01 agents.
2. Required Pack artifacts.
3. PowerShell parse validity of Pack-owned scripts only.
4. Potential unsafe `$name:` interpolation only when `name` is not a valid PowerShell scope.

Accepted scopes:
`env`, `script`, `global`, `local`, `private`, `using`.

## Explicit non-goals
- No modification to existing unrelated scripts.
- No modification to the frozen core runtime.
- No registry mutation.
- No model execution, platform access, database access, Git write, deployment, secret access, or memory write.
