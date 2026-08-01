from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.report import SQLitePlanningReportRepository
from ai_poc_planner.persistence.schema import initialize_database
from tests.support.assessed_snapshot import build_assessed_snapshot


def _legacy_report_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        **{
            key: {"content": "2026年規劃，預計30天", "fact_refs": ["F001"]}
            for key in (
                "executive_summary",
                "requirement_understanding",
                "current_process_and_pain_points",
                "goals_and_proposed_success_criteria",
                "ai_suitability_explanation",
                "recommended_direction_explanation",
                "alternatives_explanation",
                "target_workflow",
                "data_needs_and_gaps",
                "deployment_comparison",
                "poc_scope",
                "in_scope",
                "out_of_scope",
                "kpi_and_acceptance_method",
                "cost_assumptions",
                "implementation_stages_and_roles",
                "risks_governance_and_human_review",
                "open_issues_and_next_actions",
            )
        },
        "synthesis": None,
    }


def test_repository_reads_pre_fix_report_json_with_digit_narration(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-report.sqlite3"
    now = datetime.now(UTC)
    connection = database_connection(database_path)
    try:
        initialize_database(connection)
        fixture = build_assessed_snapshot(
            connection,
            SelectedModelSnapshot(
                profile_id=uuid4(),
                profile_name="Legacy report profile",
                model_name="legacy-model",
            ),
        )
        report_id = uuid4()
        connection.execute(
            "INSERT INTO planning_reports "
            "(id, version_id, analysis_id, report_json, markdown, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(report_id),
                str(fixture.version_id),
                str(fixture.expected_analysis.id),
                json.dumps(_legacy_report_payload(), ensure_ascii=False),
                "2026年規劃，預計30天",
                now.isoformat(),
            ),
        )
        connection.commit()

        report = SQLitePlanningReportRepository(connection).get_by_version(
            fixture.version_id
        )
    finally:
        connection.close()

    assert report is not None
    assert report.report.executive_summary.content == "2026年規劃，預計30天"
