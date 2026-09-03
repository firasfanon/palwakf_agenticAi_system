# PalWakf Agentic AI — Flutter Command Center

Official product UI foundation for PalWakf Agentic AI.

- Arabic-first RTL
- Windows + Web
- Read-only operational visibility by default
- FastAPI Agentic APIs remain authoritative for runtime state
- React console remains transitional fallback until Flutter UAT acceptance

Default API binding:
- Web: same origin
- Desktop: http://127.0.0.1:8000
- Override: `--dart-define=AGENTIC_API_BASE=http://127.0.0.1:PORT`
