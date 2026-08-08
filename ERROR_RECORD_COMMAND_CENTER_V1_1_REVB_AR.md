# Error Record — Command Center V1.1 Rev B

## Found in V1 candidate
1. The V1 module was installed at the project root as `command_center/`, but the actual FastAPI application runs from the package root `backend/src/palwakf_local_agents`.
2. The V1 import `from command_center import mount_command_center` was not package-native and therefore was not reliably resolvable by the application.
3. `Path(__file__).resolve().parent` in `app.py` would resolve to the Python package directory rather than the project root needed for task/evidence allowlists.
4. The V1 installer copied an entire root-level `tests` directory, creating unnecessary overwrite surface.
5. The original global “no write HTTP methods” test could not apply to the whole existing app, because legacy root APIs already contain POST routes. The corrected test asserts GET-only under Command Center’s dedicated API prefix.

## Correction
Rev B packages the module and tests in their correct backend locations, patches only the known FastAPI entrypoint with explicit mount code, preserves the root legacy candidate files unchanged, and uses exact-file preimage backup.
