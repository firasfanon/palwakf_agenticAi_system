# Changelog — 2026-07-03

## MEGA_BATCH_LOCAL_AGENTS_REACT_DEPENDENCY_LOCK_DETERMINISTIC_BUILD_AND_LOCAL_BROWSER_UAT_V1

### Added
- `frontend/package-lock.json` (npm lockfileVersion 3).
- Real Vite production `frontend/dist` output.
- Preimage backup of `frontend/package.json` for rollback evidence.
- Build, HTTP UAT, source-contract, browser-block, and test-reconciliation evidence.

### Verified
- npm ci with lifecycle scripts disabled.
- TypeScript no-emit check.
- Two clean deterministic builds with matching hashes.
- Conditional real-dist FastAPI mount and 10 SPA mounts by local HTTP.
- No Set-Cookie on tested SPA mounts; no token persistence or write literals in read-only client/bundle.

### Not changed
- Backend code, React source code, databases, model/pilot settings, write authorization, deployment configuration.

### Not accepted
- Browser-rendered UAT, due managed browser policy.
- Backend pytest suite as a whole, due 6 contract reconciliation failures.
- Production/pilot/react write enablement.
