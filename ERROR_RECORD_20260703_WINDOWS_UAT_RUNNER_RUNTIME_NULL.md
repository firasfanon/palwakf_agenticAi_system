# Error Record — Windows UAT Runner Runtime null expression

- **Observed:** 2026-07-03 after V3 parser/static pass.
- **Symptom:** runner stops immediately after `DEPENDENCY_MODE=Registry` and prints `You cannot call a method on a null-valued expression`.
- **Root cause:** direct `.Trim()` calls on potentially null external command output before runtime dependency diagnostics were written.
- **Impact:** no UAT, browser, service, model, database or production action completed.
- **Fix:** V4 null-safe external command capture, explicit stage markers, and non-masking failure record.
- **Baseline:** prior V3 static gate accepted; V4 is tools-only and does not update accepted application baseline.
