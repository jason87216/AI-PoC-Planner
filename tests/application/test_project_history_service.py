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
