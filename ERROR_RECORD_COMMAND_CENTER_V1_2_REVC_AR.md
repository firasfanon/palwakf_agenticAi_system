# Error Record — Command Center V1.1 Rev B Static Gate

## Observed failure
`FINAL_RESULT=FAIL`
`VALIDATION_FAILURES=FORBIDDEN_RUNTIME_TOKEN=requests|...\__pycache__\router.cpython-312.pyc`

## Evidence
- Unit tests: 4/4 passed.
- Command Center route probe: 10 routes, GET-only, health `READ_ONLY_READY`.
- The failure file is compiled Python bytecode, not a source file.

## Root cause
Static Gate recursively scanned binary/cache artifacts and treated a byte sequence as a runtime token.

## Remediation
Restrict Static Gate scanning to explicit text-source extensions and exclude `__pycache__`/`.pyc`.

## Risk
Low. The repair changes validation hygiene only and preserves source scanning of Command Center code.
