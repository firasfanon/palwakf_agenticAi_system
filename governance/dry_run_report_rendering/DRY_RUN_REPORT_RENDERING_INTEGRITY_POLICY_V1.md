# Dry Run Report Rendering Integrity Policy V1

- A zero-flag evidence item must render `NO_DETECTED_SECURITY_FLAG`.
- Null or blank array placeholders are not security flags.
- Markdown fences in PowerShell double-quoted Here-Strings must use a literal variable rather than raw backticks.
- Report formatting defects block model execution because human review relies on clear evidence rendering.
