# Changelog — Command Center V1.2 Rev D

- Removes generic `.replace()` from filesystem write detection.
- Retains explicit `os.replace(...)` mutation detection.
- Applies filesystem mutation scanning to Python sources only.
- Adds frontend non-GET method scanning.
- Adds deterministic evals for harmless string replace, Python write rejection, and web POST rejection.
- Runtime files, FastAPI mounting, task state, and Core Runtime remain untouched.
