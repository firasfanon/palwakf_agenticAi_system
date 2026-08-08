from palwakf_local_agents.agentic_os_v2 import (
    FOUNDATION_V2_PROHIBITED_ACTIONS,
    foundation_v2_is_execution_allowed,
)

def test_foundation_v2_execution_is_disabled():
    assert foundation_v2_is_execution_allowed() is False

def test_foundation_v2_prohibits_platform_and_database_mutation():
    assert "platform_mutation" in FOUNDATION_V2_PROHIBITED_ACTIONS
    assert "database_access" in FOUNDATION_V2_PROHIBITED_ACTIONS
