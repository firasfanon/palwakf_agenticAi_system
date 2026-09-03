from pathlib import Path

import pytest

from palwakf_local_agents.agentic_core_v1.intersystem_v1 import (
    WorkspaceAuthorityPackageV1,
    execute_integration_pilot,
)
from palwakf_local_agents.agentic_core_v1.learning_service import AgenticLearningService

BASE = "1807b450f17904d17cfbe418ded7d61ee5029b56"
SOURCE = "19b9c8e9d2c52b955dfb1fd273dfecaa4f8383e6"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _package(expected_head=SOURCE):
    return WorkspaceAuthorityPackageV1(
        state_package_id="workspace-state-pilot-001",
        execution_run_id="FOUR_SYSTEM_PILOT_RUN_001",
        project_id="PALWAKF_LOCAL_AGENTS",
        task_id="FOUR_SYSTEM_READ_ONLY_INTEGRATION_PILOT_V1",
        repository="firasfanon/palwakf_agenticAi_system",
        task_branch="task/FOUR_SYSTEM_READ_ONLY_INTEGRATION_PILOT_V1",
        base_sha=BASE,
        expected_head=expected_head,
        authority_reference="AUTHORITY:FOUR_SYSTEM_READ_ONLY_INTEGRATION_PILOT_V1",
        objective="Perform a governed read-only diagnostic and derive a learning candidate.",
        constraints=["NO_MUTATION"],
        timeout_seconds=300,
        scope_patterns=["backend/**"],
        required_capabilities=["READ_ONLY_DIAGNOSTIC"],
        required_tests=["AGENTIC_CONTRACT"],
    )


def test_canonical_workspace_package_executes_and_emits_mind_bundle():
    root = _root()
    result = execute_integration_pilot(
        learning=AgenticLearningService(project_root=root, source_commit_sha=SOURCE),
        package=_package(),
        project_root=root,
        source_commit_sha=SOURCE,
    )
    assert result.execution["final_result"] == "PASS"
    assert result.evaluation["passed"] is True
    assert result.institutional_knowledge_promoted is False
    assert result.external_review_required is True
    assert result.learning_bundle.auto_promotion is False
    assert result.learning_bundle.source_sha == SOURCE
    assert len(result.learning_bundle.candidates) == 1
    assert result.execution["authorized_scope"]["allowed_path_patterns"] == ["backend/**"]
    manifest = result.execution["observations"][0]["manifest_sample"]
    assert manifest
    assert all(item["path"].startswith("backend/") for item in manifest)
    assert all(".palwakf_apply_backup" not in item["path"] for item in manifest)


def test_canonical_workspace_package_rejects_stale_expected_head():
    root = _root()
    with pytest.raises(ValueError, match="INTERSYSTEM_EXPECTED_HEAD_SOURCE_MISMATCH"):
        execute_integration_pilot(
            learning=AgenticLearningService(project_root=root, source_commit_sha=SOURCE),
            package=_package(expected_head="0" * 40),
            project_root=root,
            source_commit_sha=SOURCE,
        )
