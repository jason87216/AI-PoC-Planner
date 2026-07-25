from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_poc_planner.application.discovery_interview import DiscoveryInterviewService
from ai_poc_planner.domain.discovery import (
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
        output, [existing], 2
    )

    assert normalized.questions[0].fact_key == "clarification_round_2_question_1"
