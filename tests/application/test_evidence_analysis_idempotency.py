from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ai_poc_planner.application.evidence_analysis import EvidenceAnalysisService
from ai_poc_planner.application.project_history import ProjectHistoryService
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.discovery import SQLiteDiscoveryRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database
from ai_poc_planner.persistence.solution_catalog import SQLiteSolutionCatalogRepository
from tests.support.assessed_snapshot import build_assessed_snapshot


def test_existing_assessment_is_returned_without_provider_or_duplicate_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "idempotency.sqlite3"
    connection = database_connection(database_path)
    try:
        initialize_database(connection)
        fixture = build_assessed_snapshot(
            connection,
            SelectedModelSnapshot(
                profile_id=uuid4(),
                profile_name="Test profile",
                model_name="test-model",
            ),
        )
        history = ProjectHistoryService(
            SQLiteProjectHistoryRepository(connection),
            selected_profile_getter=lambda: None,
        )
        provider_calls: list[object] = []

        def fail_if_called(_: object) -> object:
            provider_calls.append(object())
            raise AssertionError("provider must not be called")

        service = EvidenceAnalysisService(
            history=history,
            sessions=SQLiteDiscoveryRepository(connection),
            analyses=SQLiteAnalysisRepository(connection),
            readiness=object(),
            selected_profile_getter=lambda: None,
            adapter_factory=fail_if_called,
            catalog=SQLiteSolutionCatalogRepository(connection),
        )
        assert service.create(fixture.project_id, 1) == fixture.expected_analysis
        assert provider_calls == []
    finally:
        connection.close()
