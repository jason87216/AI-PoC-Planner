from __future__ import annotations

from uuid import uuid4

from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database
from tests.support.assessed_snapshot import build_assessed_snapshot


def test_builds_reloadable_assessed_snapshot(tmp_path) -> None:
    database_path = tmp_path / "snapshot.sqlite3"
    connection = database_connection(database_path)
    try:
        initialize_database(connection)
        fixture = build_assessed_snapshot(
            connection,
            SelectedModelSnapshot(
                profile_id=uuid4(),
                profile_name="NVIDIA",
                model_name="openai/gpt-oss-20b",
            ),
        )
        assert fixture.expected_analysis.weighted_total == 60
        assert fixture.expected_analysis.recommended_option_key == "o2"
    finally:
        connection.close()
    reloaded = database_connection(database_path)
    try:
        history = SQLiteProjectHistoryRepository(reloaded)
        assert (
            history.get_version(fixture.project_id, 1).status is ProjectStatus.ASSESSED
        )
        assert (
            SQLiteAnalysisRepository(reloaded).get_by_version(fixture.version_id)
            == fixture.expected_analysis
        )
    finally:
        reloaded.close()
