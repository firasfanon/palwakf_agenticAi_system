# V1.0.4 Timeout Retry Repair Record

## Evidence

- Evidence ZIP SHA-256: `EF5C9AC4F5E1623980DFBF1D19B20B9F3568F95938ED3FD07D3966528DA19686`
- Candidate generate response: HTTP 502
- Detail code: `MODEL_PROVIDER_REQUEST_FAILED`
- Detail type: `TimeoutError`
- Request duration: approximately 91 seconds
- No Run persisted
- No Candidate persisted
- Source mutation false

## Patch

- Switch one controlled retry to `qwen2.5:3b`.
- Set OpenAPI maximum timeout `180`.
- Set bounded output `1200`.
- Set deterministic temperature `0.0`.
- Require an exact new authorization token.
- Enforce one attempt and no automatic retry.
- Record failure classification automatically.
- Preserve Loopback-only and Candidate Workspace-only boundaries.
