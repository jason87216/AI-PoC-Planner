from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ai_poc_planner.application.case_centered_assessment import (
    build_case_centered_assessment,
)
from ai_poc_planner.domain.catalog import OpportunityType
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.infrastructure.local_case_repository import LocalCaseRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.schema import initialize_database
from tests.application.test_case_centered_assessment import _case, _facts
from tests.support.assessed_snapshot import build_assessed_snapshot


def test_case_centered_result_survives_analysis_snapshot_reload(tmp_path: Path) -> None:
    database_path = tmp_path / "case-centered.sqlite3"
    case_centered = build_case_centered_assessment(
        cases=LocalCaseRepository(
            Path(__file__).parents[2] / "data" / "reviewed_cases.json"
        ).load()
        + (_case(),),
        facts=_facts(),
        opportunity_types=(
            OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST,
        ),
        recommendation_title="權限申請標準化與人工審核輔助",
        gate_results=(),
        option_kind="hybrid",
    )
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
            case_centered=case_centered,
        )
        assert fixture.expected_analysis.case_centered == case_centered
    finally:
        connection.close()
