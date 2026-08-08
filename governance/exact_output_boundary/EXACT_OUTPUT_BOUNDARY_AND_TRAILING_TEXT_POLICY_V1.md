# Exact Output Boundary and Trailing Text Policy V1

## Purpose
This policy constrains the local model response for the read-only evidence pilot.

## Mandatory response format
The model must return exactly 13 lines:

1. `OUTPUT_CONTRACT_START`
2–12. The 11 ordered contract key/value lines
13. `OUTPUT_CONTRACT_END`

No text may appear before the start boundary or after the end boundary.

## Trailing text
Any non-empty text after `OUTPUT_CONTRACT_END` is rejected. The validator records:
- `TRAILING_NONCONTRACT_TEXT_DETECTED`
- trailing line count
- SHA-256 of the trailing text

The validator is not relaxed to accept additions such as `REFERENCE_EVIDENCE`, `NOTES`, explanations, Markdown, or code fences.

## Safety
- Reference content remains untrusted and non-executable.
- The model has read-only scope only.
- No memory acceptance is automatic.
- No SQL, Git write, deployment, database access, platform mutation, or secrets access is authorized.
