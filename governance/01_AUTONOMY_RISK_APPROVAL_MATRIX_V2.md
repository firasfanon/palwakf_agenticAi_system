# Autonomy, Risk and Approval Matrix V2

## Autonomy levels
| Level | Meaning | V2 availability |
|---|---|---|
| L0_READ_ONLY | Read, classify, summarize, trace, assess evidence | Enabled only after role admission |
| L1_PLAN_ONLY | Propose plans, contracts, UX, architecture, test plans, drafts | Enabled only after role admission |
| L2_PATCH_ALLOWED | Isolated low-risk patch in file allowlist | Disabled |
| L3_BATCH_ALLOWED | Approved local batch plus tests | Disabled |
| L4_REVIEW_REQUIRED | Sensitive implementation with independent review | Disabled |
| L5_STAGING_DEPLOY | Staging deployment | Disabled |
| L6_PRODUCTION_RESTRICTED | Production action with explicit human approval | Disabled |

## Risk matrix
| Risk | Examples | Minimum workflow |
|---|---|---|
| LOW | documentation, classification, static inventory | L0/L1 + self-check |
| MEDIUM | UX contract, architecture plan, test plan | L1 + human review when adopted |
| HIGH | auth, RLS, database, uploads, permissions | no execution in V2; plan + independent review |
| CRITICAL | production, destructive deletion, secrets, payments | human decision only; no local-agent execution |

## Promotion rule
A role is promoted only through a versioned admission batch containing:
- specific scope and tool allowlist,
- expected and forbidden behavior,
- deterministic validation,
- negative cases,
- human acceptance,
- regression cases.
