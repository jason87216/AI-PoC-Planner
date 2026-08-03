from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_poc_planner.application.project_history import ProjectHistoryService
from ai_poc_planner.domain.enums import FactStatus, InterviewRole
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    FactCorrectionRequiredError,
    FactNotCurrentError,
)
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database


def test_assumption_confirmation_and_explicit_correction_keep_revision_history(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "history.sqlite3")
    initialize_database(connection)
    service = ProjectHistoryService(
        SQLiteProjectHistoryRepository(connection),
        clock=lambda: datetime(2026, 7, 24, tzinfo=UTC),
    )
    try:
        project, version = service.create_project("Support")
        understanding = service.append_message(
            project.id,
            1,
            role=InterviewRole.ASSISTANT,
            message_kind="ai_understanding",
            content="The owner is operations.",
        )
        confirmation = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="confirmation",
            content="Confirmed.",
        )
        correction = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="correction",
            content="The owner is service operations.",
        )
        assumption = service.propose_assumption(
            project.id,
            1,
            fact_key="owner",
            value="operations",
            reference_message_ids=[understanding.id],
        )
        confirmed = service.confirm_assumption(
            project.id,
            1,
            assumption.id,
            reference_message_ids=[confirmation.id],
        )
        with pytest.raises(FactCorrectionRequiredError):
            service.propose_assumption(
                project.id,
                1,
                fact_key=" OWNER ",
                value="different",
                reference_message_ids=[understanding.id],
            )
        corrected = service.correct_fact(
            project.id,
            1,
            confirmed.id,
            status=FactStatus.CONFIRMED,
            value="service operations",
            correction_reason="User corrected ownership.",
            reference_message_ids=[correction.id],
        )

        assert service.list_current_facts(project.id, 1) == [corrected]
        assert [item.id for item in service.list_fact_history(project.id, 1)] == [
            assumption.id,
            confirmed.id,
            corrected.id,
        ]
        with pytest.raises(FactNotCurrentError):
            service.confirm_assumption(
                project.id,
                1,
                assumption.id,
                reference_message_ids=[confirmation.id],
            )
    finally:
        connection.close()


def test_interview_can_resolve_initial_missing_fact_with_superseding_evidence(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "interview-revision.sqlite3")
    initialize_database(connection)
    service = ProjectHistoryService(SQLiteProjectHistoryRepository(connection))
    try:
        project, _ = service.create_project("Interview revision")
        brief = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="user_input",
            content="Minimal brief.",
        )
        missing = service.record_unknown_or_missing(
            project.id,
            1,
            fact_key="desired_outcome",
            status=FactStatus.MISSING,
            reference_message_ids=[brief.id],
        )
        answer = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="answer",
            content="減少人工重工。",
        )
        confirmed = service.resolve_open_fact_from_interview(
            project.id,
            1,
            missing.id,
            status=FactStatus.CONFIRMED,
            value="減少人工重工。",
            reference_message_ids=[answer.id],
        )

        assert service.list_current_facts(project.id, 1) == [confirmed]
        assert confirmed.supersedes_fact_id == missing.id
        assert confirmed.reference_message_ids == [answer.id]
        assert [item.id for item in service.list_fact_history(project.id, 1)] == [
            missing.id,
            confirmed.id,
        ]
    finally:
        connection.close()


def test_interview_gap_revision_keeps_unknown_and_missing_states_auditable(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "interview-gap-revision.sqlite3")
    initialize_database(connection)
    service = ProjectHistoryService(SQLiteProjectHistoryRepository(connection))
    try:
        project, _ = service.create_project("Interview gap revision")
        brief = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="user_input",
            content="Minimal brief.",
        )
        missing = service.record_unknown_or_missing(
            project.id,
            1,
            fact_key="available_data",
            status=FactStatus.MISSING,
            reference_message_ids=[brief.id],
        )
        answer = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="answer",
            content="目前不清楚。",
        )
        unknown = service.resolve_open_fact_from_interview(
            project.id,
            1,
            missing.id,
            status=FactStatus.UNKNOWN,
            value=None,
            reference_message_ids=[answer.id],
        )

        assert unknown.status is FactStatus.UNKNOWN
        assert unknown.supersedes_fact_id == missing.id
        assert unknown.reference_message_ids == [answer.id]
        assert len(service.list_fact_history(project.id, 1)) == 2

        confirmed = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="answer",
            content="New data.",
        )
        resolved = service.resolve_open_fact_from_interview(
            project.id,
            1,
            unknown.id,
            status=FactStatus.CONFIRMED,
            value="New data.",
            reference_message_ids=[confirmed.id],
        )
        assert resolved.status is FactStatus.CONFIRMED
        assert resolved.supersedes_fact_id == unknown.id
    finally:
        connection.close()


def test_confirmed_fact_still_requires_explicit_correction_flow(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "confirmed-interview.sqlite3")
    initialize_database(connection)
    service = ProjectHistoryService(SQLiteProjectHistoryRepository(connection))
    try:
        project, _ = service.create_project("Confirmed interview")
        message = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="user_input",
            content="Initial answer.",
        )
        confirmed = service.record_user_confirmed_fact(
            project.id,
            1,
            fact_key="desired_outcome",
            value="原本成果",
            reference_message_ids=[message.id],
        )
        answer = service.append_message(
            project.id,
            1,
            role=InterviewRole.USER,
            message_kind="answer",
            content="不同成果",
        )

        with pytest.raises(FactCorrectionRequiredError):
            service.resolve_open_fact_from_interview(
                project.id,
                1,
                confirmed.id,
                status=FactStatus.CONFIRMED,
                value="不同成果",
                reference_message_ids=[answer.id],
            )
    finally:
        connection.close()
