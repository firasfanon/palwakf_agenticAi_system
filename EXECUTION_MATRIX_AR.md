# Execution Matrix

| Layer | Apply | Deferred |
|---|---:|---:|
| React source | Yes | — |
| app.py conditional mount | Yes | — |
| npm/pnpm dependency install | No | Separate explicit authorization |
| Vite build to dist | No | Separate explicit authorization |
| Legacy static UI removal | No | Future migration only |
| API/AuthZ backend contracts | No | Full Stack Vertical Slices |
| Model/Pilot execution | No | Independently governed |
