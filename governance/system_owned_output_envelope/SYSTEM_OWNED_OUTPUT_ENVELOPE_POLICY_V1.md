# System-Owned Output Envelope Policy V1

## Ownership
The model owns only the 11-line body. The host owns `OUTPUT_CONTRACT_START` and `OUTPUT_CONTRACT_END`.

## Rejection
Any raw provider output that does not contain exactly 11 non-blank ordered lines is rejected. Extra lines, headings, Markdown, boundaries, notes, or reference restatement are invalid.

## Evidence
- Raw provider output remains immutable evidence.
- Canonical output exists only when body validation passes.
- Canonical output is created deterministically by the host.

## Scope
This policy applies only to the local read-only evidence pilot. It does not authorize platform mutation, database access, Git write, deployment, secrets access, or automatic learning.
