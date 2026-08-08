# PALWAKF Local Agents — Product Start Screen Baseline Record

## LOCAL_AGENTS_PRODUCT_START_SCREEN_R1_ACCEPTED_20260707

- **Authorization:** `AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_BASELINE_PROMOTION_EVIDENCE_ARCHIVE_AND_GUIDE_UPDATE_V1`.
- **Promoted candidate:** `PRODUCT_CANDIDATE_R1`.
- **Accepted surface:** `/agent-console`, React/TypeScript Arabic RTL; desktop and mobile navigation/drawer verified.
- **Browser UAT:** Playwright Core with locally installed Edge, non-persistent contexts, screenshots/DOM/traces.
- **Acceptance boundaries:** application network requests are `GET` only; `credentials: omit`; no credential headers; no React write controls; no database/SQLite writes; no model, pilot, commercial, or production execution.
- **Harness policy:** Playwright is the accepted browser UAT harness. Custom CDP/DevTools harness is retired and must not be reused for acceptance.
- **Narrow exception:** `/favicon.ico` was the sole `404` in R11; it is classified `NON_BLOCKING_FAVICON_404`, not an application API or operational asset failure.
- **Evidence location after promotion:** `ACCEPTED_BASELINES/LOCAL_AGENTS_PRODUCT_START_SCREEN_R1_ACCEPTED_20260707/EVIDENCE/WINDOWS_PLAYWRIGHT_UAT_R11_20260707_123749`.
- **Continuation rule:** later changes begin from this baseline and remain read-only unless an independently authorized write/execution scope is approved.

