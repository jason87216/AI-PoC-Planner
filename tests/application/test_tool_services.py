from datetime import UTC, datetime
from uuid import UUID

import pytest

from ai_poc_planner.application.tool_services import (
    TOOL_NAMES,
    run_assessment_tools,
)
from ai_poc_planner.domain.enums import EvidenceSourceType, ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject, EvidenceReference
from ai_poc_planner.domain.tools import AssessmentToolOutputs
from ai_poc_planner.providers.base import PreparationStatus, ProviderRequest
from ai_poc_planner.providers.fake import FakeModelProvider

PROJECT_ID = UUID("10000000-0000-0000-0000-000000000011")
SESSION_ID = UUID("20000000-0000-0000-0000-000000000011")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000011")


def _preparation(scenario: str = "high_value_low_risk"):
    timestamp = datetime(2026, 7, 19, tzinfo=UTC)
    project = AnalysisProject(
        id=PROJECT_ID,
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.INTERVIEWING,
        created_at=timestamp,
        updated_at=timestamp,
    )
    request = ProviderRequest(
        project=project,
        session_id=SESSION_ID,
        interview_answers={
            "scenario": scenario,
            "target_users": ["客服人員"],
            "current_workflow": "人工搜尋已核准的產品文件。",
            "data_sources": ["核准產品文件", "代表性問題集"],
            "owner": "客服流程負責人",
        },
        evidence=[
            EvidenceReference(
                id=EVIDENCE_ID,
                project_id=PROJECT_ID,
                session_id=SESSION_ID,
                source_type=EvidenceSourceType.INTERVIEW,
                source_ref="interview:tool-test:1",
                label="固定訪談資料",
            )
        ],
    )
    result = FakeModelProvider().prepare_assessment(request)
    assert result.status is PreparationStatus.READY
    assert result.facts is not None
    assert result.tool_inputs is not None
    return result


def test_all_six_tool_services_return_success_envelopes() -> None:
    preparation = _preparation()

    outputs = run_assessment_tools(preparation.tool_inputs, preparation.facts)

    assert isinstance(outputs, AssessmentToolOutputs)
    assert all(getattr(outputs, name).error is None for name in TOOL_NAMES)


def test_fixture_lookup_is_explicit_deterministic_and_owned() -> None:
    preparation = _preparation()

    first = run_assessment_tools(preparation.tool_inputs, preparation.facts)
    second = run_assessment_tools(preparation.tool_inputs, preparation.facts)
    retrieval = first.retrieve_similar_cases

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert retrieval is not None
    assert retrieval.cases
    assert retrieval.evidence
    assert all(item.project_id == PROJECT_ID for item in retrieval.evidence)
    assert all(item.session_id == SESSION_ID for item in retrieval.evidence)
    assert all(item.source_ref.startswith("fixture:") for item in retrieval.evidence)


def test_tools_do_not_return_final_assessment_decisions() -> None:
    preparation = _preparation()

    payload = run_assessment_tools(
        preparation.tool_inputs, preparation.facts
    ).model_dump(mode="json")

    assert "weighted_score" not in payload
    assert "recommendation" not in payload


def test_risk_tool_matches_m13_gate_rules_without_owning_recommendation() -> None:
    preparation = _preparation("high_score_but_blocked")

    risk = run_assessment_tools(
        preparation.tool_inputs, preparation.facts
    ).evaluate_risk_and_hard_gates

    assert risk is not None
    assert risk.gate_disposition.value == "blocked"
    assert [gate.rule_id for gate in risk.hard_gates] == ["HG-01"]


@pytest.mark.parametrize("tool_name", TOOL_NAMES)
def test_runner_returns_existing_error_envelope_for_selected_tool(
    tool_name: str,
) -> None:
    preparation = _preparation()

    outputs = run_assessment_tools(
        preparation.tool_inputs,
        preparation.facts,
        fail_tool=tool_name,
    )
    failed = getattr(outputs, tool_name)

    assert failed.error is not None
    assert failed.error.code == "simulated_tool_error"
    assert failed.project_id == PROJECT_ID
    assert failed.session_id == SESSION_ID


def test_runner_rejects_unknown_failure_target() -> None:
    preparation = _preparation()

    with pytest.raises(ValueError, match="unknown tool"):
        run_assessment_tools(
            preparation.tool_inputs,
            preparation.facts,
            fail_tool="not_a_tool",
        )
