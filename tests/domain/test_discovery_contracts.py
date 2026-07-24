from uuid import uuid4

import pytest
from pydantic import ValidationError

from ai_poc_planner.application.discovery_interview import normalize_available_data
from ai_poc_planner.domain.discovery import (
    InitialBrief,
    InterviewAnswer,
    InterviewQuestionOutput,
    InterviewRoundOutput,
)
from ai_poc_planner.domain.enums import AvailableDataStatus, InterviewAnswerStatus


def test_initial_brief_trims_required_fields_and_rejects_extra_notes() -> None:
    brief = InitialBrief(
        project_name="  Discovery  ",
        current_workflow_problem=" workflow ",
        desired_outcome=" outcome ",
        available_data=" data ",
    )

    assert brief.project_name == "Discovery"
    with pytest.raises(ValidationError):
        InitialBrief(
            project_name="x",
            current_workflow_problem="x",
            desired_outcome="x",
            available_data="x",
            supplementary_notes="not accepted",
        )


def test_available_data_normalization_uses_exact_tokens_only() -> None:
    assert normalize_available_data("不知道") is AvailableDataStatus.UNKNOWN
    assert normalize_available_data("目前没有") is AvailableDataStatus.MISSING
    assert normalize_available_data("不知道是否完整") is AvailableDataStatus.KNOWN


def test_interview_output_and_answer_invariants_are_strict() -> None:
    question = InterviewQuestionOutput(
        fact_key="volume",
        question="How many?",
        why_it_matters="Sizing",
        affected_judgement="data readiness",
        example="monthly count",
    )
    assert InterviewRoundOutput(
        interview_complete=False, questions=[question]
    ).questions
    with pytest.raises(ValidationError):
        InterviewRoundOutput(interview_complete=True, questions=[question])
    with pytest.raises(ValidationError):
        InterviewAnswer(
            question_id=uuid4(), answer_status=InterviewAnswerStatus.UNKNOWN, answer="x"
        )


def test_question_rejects_provider_internal_requests() -> None:
    with pytest.raises(ValidationError):
        InterviewQuestionOutput(
            fact_key="x",
            question="What is the API key?",
            why_it_matters="x",
            affected_judgement="x",
            example="x",
        )
