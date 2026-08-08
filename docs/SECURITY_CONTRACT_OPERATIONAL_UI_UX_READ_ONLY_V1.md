# Security Contract

- Allowed mutation: exactly three existing static assets.
- All network calls target existing `/api/v1/local-agents/*` read surfaces.
- Explicit non-GET HTTP methods are forbidden.
- Browser persistence writes are forbidden.
- `app.py`, router, store, tests, task/review state remain unchanged.
- Model execution remains `NONE`; Pilot execution remains `NOT_EXECUTED`.
