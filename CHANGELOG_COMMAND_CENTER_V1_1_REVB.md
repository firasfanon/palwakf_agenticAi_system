# Changelog — Command Center V1.1 Rev B

## Corrected integration
- Moved Command Center Python module into the distributable backend package:
  `backend/src/palwakf_local_agents/command_center`.
- Added exact FastAPI mount patch for the actual entrypoint:
  `backend/src/palwakf_local_agents/app.py`.
- Corrected project root derivation to `Path(__file__).resolve().parents[3]`.
- Moved Command Center test to `backend/tests`.
- Narrowed installer scope to exact files; it no longer overwrites an entire root-level `tests` directory.
- Retains root-level legacy `command_center/` unchanged and unused.
- Clarified that GET-only guarantees apply to the Command Center API prefix, not pre-existing legacy endpoints in the base application.
