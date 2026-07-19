from uuid import UUID

import pytest

from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.tool_services import run_assessment_tools
from ai_poc_planner.application.workflow import (
    AssessmentWorkflowError,
    ClarificationRequiredError,
    ProviderWorkflowError,
    ToolWorkflowError,
    run_offline_planning,
)
from ai_poc_planner.assessment.engine import assess_project
from ai_poc_planner.domain.enums import GateDisposition, Recommendation
from ai_poc_planner.domain.workflow import AssessmentInput
from ai_poc_planner.providers.base import ProviderRequest
from ai_poc_planner.providers.fake import FakeModelProvider


@pytest.mark.parametrize(
    ("scenario", "disposition", "recommendation"),
    [
        ("high_value_low_risk", GateDisposition.PASS, Recommendation.RECOMMENDED),
        (
            "high_score_but_blocked",
            GateDisposition.BLOCKED,
            Recommendation.NOT_RECOMMENDED,
        ),
        (
            "assistive_only",
            GateDisposition.ASSISTIVE_ONLY,
            Recommendation.CONDITIONAL,
        ),
        (
            "requires_controls",
            GateDisposition.REQUIRES_CONTROLS,
            Recommendation.CONDITIONAL,
        ),
    ],
)
def test_offline_workflow_preserves_m13_outcomes(
    scenario: str,
    disposition: GateDisposition,
    recommendation: Recommendation,
) -> None:
    result = run_offline_planning(build_demo_request(scenario=scenario))

    assert result.assessment.weighted_score == 100
    assert result.assessment.gate_disposition is disposition
    assert result.assessment.recommendation is recommendation
    assert result.proposal.weighted_score == result.assessment.weighted_score
    assert result.proposal.gate_disposition is disposition
    assert result.proposal.recommendation is recommendation


def test_workflow_is_deterministic_and_does_not_mutate_request() -> None:
    request = build_demo_request()
    before = request.model_dump(mode="json")

    first = run_offline_planning(request)
    second = run_offline_planning(request)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert request.model_dump(mode="json") == before


def test_workflow_assessment_equals_direct_m13_engine_call() -> None:
    request = build_demo_request()
    preparation = FakeModelProvider().prepare_assessment(
        ProviderRequest(
            project=request.project,
            session_id=request.session_id,
            interview_answers=request.interview_answers,
            evidence=request.evidence,
        )
    )
    assert preparation.facts is not None
    assert preparation.tool_inputs is not None
    outputs = run_assessment_tools(preparation.tool_inputs, preparation.facts)
    direct = assess_project(
        AssessmentInput(
            schema_version="1.0",
            project_id=request.project.id,
            session_id=request.session_id,
            assessment_id=request.assessment_id,
            evaluated_at=request.evaluated_at,
            known_information=request.interview_answers,
            facts=preparation.facts,
            tool_outputs=outputs,
            evidence=request.evidence,
        )
    )

    assert run_offline_planning(request).assessment == direct


def test_provider_error_has_stable_application_error() -> None:
    request = build_demo_request()
    answers = {**request.interview_answers, "simulate_provider_error": True}

    with pytest.raises(ProviderWorkflowError) as error:
        run_offline_planning(request.model_copy(update={"interview_answers": answers}))

    assert error.value.code == "provider_error"


def test_clarification_required_returns_typed_questions() -> None:
    request = build_demo_request().model_copy(update={"interview_answers": {}})

    with pytest.raises(ClarificationRequiredError) as error:
        run_offline_planning(request)

    assert error.value.code == "clarification_required"
    assert 1 <= len(error.value.questions) <= 5


def test_tool_error_has_stable_application_error() -> None:
    request = build_demo_request().model_copy(
        update={"fail_tool": "assess_data_readiness"}
    )

    with pytest.raises(ToolWorkflowError) as error:
        run_offline_planning(request)

    assert error.value.code == "assessment_tool_error"


def test_cross_project_evidence_has_stable_assessment_error() -> None:
    request = build_demo_request()
    evidence = request.evidence[0].model_copy(
        update={"project_id": UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")}
    )

    with pytest.raises(AssessmentWorkflowError) as error:
        run_offline_planning(request.model_copy(update={"evidence": [evidence]}))

    assert error.value.code == "invalid_evidence_ownership"
