# Changelog — Workspace Core Operational UI/UX Language Closure V1

## Added
- Arabic operational display labels for workspace type, policy, lifecycle, execution state, legacy status, and readiness controls.
- Collapsed raw technical details panel for review-only access to source values.
- Keyboard-accessible workspace cards and one-time event delegation.

## Changed
- Overflow-safe responsive card and detail layouts.
- Long internal enum values are no longer rendered as primary card content.

## Preserved
- Core/API/policy values remain unchanged.
- Read-only workspace API remains GET-only.
- No execution, model, Pilot, workspace creation, policy mutation, or cross-workspace access was added.
