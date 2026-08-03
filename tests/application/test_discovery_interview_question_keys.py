from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_poc_planner.application.discovery_interview import DiscoveryInterviewService
from ai_poc_planner.domain.discovery import (
    InterviewQuestion,
    InterviewQuestionOutput,
    InterviewRoundOutput,
)
from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.project_history import FactRevision


def test_interview_questions_reuse_stable_new_keys_for_current_facts() -> None:
    output = InterviewRoundOutput(
        interview_complete=False,
        questions=[
            InterviewQuestionOutput(
                fact_key="current_workflow_problem",
                question="What is the workflow?",
                why_it_matters="It shapes the scope.",
                affected_judgement="Fit",
                example="A brief description is enough.",
            )
        ],
    )
    existing = FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="current_workflow_problem",
        value="Manual routing",
        status=FactStatus.CONFIRMED,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )

    normalized = DiscoveryInterviewService._with_unique_question_keys(
        output, [existing]
    )

    assert normalized.interview_complete is True
    assert normalized.questions == []


def test_duplicate_question_text_is_dropped_without_renaming() -> None:
    output = InterviewRoundOutput(
        interview_complete=False,
        questions=[
            InterviewQuestionOutput(
                fact_key="new_key",
                question="How is the workflow approved?",
                why_it_matters="It affects governance.",
                affected_judgement="hard gate",
                example="A short answer is enough.",
            )
        ],
    )
    previous = InterviewQuestion(
        id=uuid4(),
        session_id=uuid4(),
        version_id=uuid4(),
        round_number=1,
        position=1,
        visible_message_id=uuid4(),
        fact_key="approval_flow",
        question="How is the workflow approved?",
        why_it_matters="It affects governance.",
        affected_judgement="hard gate",
        example="A short answer is enough.",
        created_at=datetime.now(UTC),
    )

    normalized = DiscoveryInterviewService._with_unique_question_keys(
        output, [], [previous]
    )

    assert normalized.interview_complete is True
    assert normalized.questions == []


def test_initial_missing_fact_can_be_asked_once() -> None:
    output = InterviewRoundOutput(
        interview_complete=False,
        questions=[
            InterviewQuestionOutput(
                fact_key="desired_outcome",
                question="希望改善的成果是什麼？",
                why_it_matters="這會影響成功方向。",
                affected_judgement="success direction",
                example="描述希望改善的結果即可。",
            )
        ],
    )
    missing = FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="desired_outcome",
        value=None,
        status=FactStatus.MISSING,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )

    normalized = DiscoveryInterviewService._with_unique_question_keys(output, [missing])

    assert normalized.interview_complete is False
    assert [item.fact_key for item in normalized.questions] == ["desired_outcome"]


def test_previously_asked_missing_fact_is_not_asked_again() -> None:
    output = InterviewRoundOutput(
        interview_complete=False,
        questions=[
            InterviewQuestionOutput(
                fact_key="desired_outcome",
                question="希望改善的成果是什麼？",
                why_it_matters="這會影響成功方向。",
                affected_judgement="success direction",
                example="描述希望改善的結果即可。",
            )
        ],
    )
    missing = FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="desired_outcome",
        value=None,
        status=FactStatus.MISSING,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )
    previous = InterviewQuestion(
        id=uuid4(),
        session_id=uuid4(),
        version_id=uuid4(),
        round_number=1,
        position=1,
        visible_message_id=uuid4(),
        fact_key="desired_outcome",
        question="上一輪已詢問希望改善的成果。",
        why_it_matters="這會影響成功方向。",
        affected_judgement="success direction",
        example="描述希望改善的結果即可。",
        created_at=datetime.now(UTC),
    )

    normalized = DiscoveryInterviewService._with_unique_question_keys(
        output, [missing], [previous]
    )

    assert normalized.interview_complete is True
    assert normalized.questions == []


def test_complete_output_is_not_allowed_while_initial_material_gaps_remain() -> None:
    missing = FactRevision(
        id=uuid4(),
        version_id=uuid4(),
        fact_key="known_constraints",
        value=None,
        status=FactStatus.MISSING,
        reference_message_ids=[uuid4()],
        created_at=datetime.now(UTC),
    )
    output = InterviewRoundOutput(interview_complete=True, questions=[])

    assert DiscoveryInterviewService._has_unresolved_material_topics([missing], [])
    assert not DiscoveryInterviewService._covers_material_topic(output, [missing], [])


def test_only_confirmed_material_judgement_can_open_second_round() -> None:
    question = InterviewQuestion(
        id=uuid4(),
        session_id=uuid4(),
        version_id=uuid4(),
        round_number=1,
        position=1,
        visible_message_id=uuid4(),
        fact_key="available_data",
        question="有哪些資料可供整理？",
        why_it_matters="資料缺口會影響後續判斷。",
        affected_judgement="資料盤點",
        example="可提供大致類型即可。",
        created_at=datetime.now(UTC),
    )
    material_question = question.model_copy(
        update={"affected_judgement": "hard gate 與人工核准"}
    )

    assert (
        DiscoveryInterviewService._question_requires_material_follow_up(question)
        is False
    )
    assert (
        DiscoveryInterviewService._question_requires_material_follow_up(
            material_question
        )
        is True
    )
