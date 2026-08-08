# Error Record — Lifecycle Closure Rev C
## 2026-06-27

## ER-PLC-001 — Rev B recursive copy timeout

```text
STATUS=CLOSED
CAUSE=Copy-Item recursively copied $tempRoot into child $badRoot
EFFECT=Potential infinite nested directory growth and Evals timeout
FAILED_COMPONENT=Invoke-ReadOnlyPilotLifecycleClosureEvalsV1.ps1 (Rev B)
FIX=Rev C creates the negative fixture in a sibling root outside $tempRoot
VALIDATION=Rev C source guard + actual Evals 6/6 PASS
```

## ER-PLC-002 — External verification harness empty ExitCode

```text
STATUS=DOCUMENTED
CAUSE=PowerShell Start-Process object exposed empty ExitCode after WaitForExit in verification wrapper
EFFECT=Wrapper took false error branch despite completed evaluator
PROJECT_IMPACT=NONE
PROJECT_CODE_CHANGE=NONE
TRUSTED_EVIDENCE=Captured evaluator stdout with EVAL_PASSED_COUNT=6 and FINAL_RESULT=PASS
FUTURE_HARNESS_RULE=Call $proc.Refresh() before inspecting ExitCode; test for $null explicitly.
```
