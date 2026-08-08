"""Agentic OS V2 constants. No model or tool execution."""
from pathlib import Path

AUTONOMY_LEVELS = (
    "L0_READ_ONLY",
    "L1_PLAN_ONLY",
    "L2_PATCH_ALLOWED",
    "L3_BATCH_ALLOWED",
    "L4_REVIEW_REQUIRED",
    "L5_STAGING_DEPLOY",
    "L6_PRODUCTION_RESTRICTED",
)

FOUNDATION_V2_PROHIBITED_ACTIONS = (
    "platform_mutation",
    "database_access",
    "network_write",
    "git_write",
    "deployment",
    "secrets_access",
    "self_promotion",
)

def foundation_v2_is_execution_allowed() -> bool:
    """V2 is contract-only by default."""
    return False
