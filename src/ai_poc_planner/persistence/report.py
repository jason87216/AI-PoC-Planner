"""Immutable SQLite persistence for validated Phase 5.2 reports."""

# ruff: noqa: E501

from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from ai_poc_planner.domain.planning_report import (
    PersistedPlanningReport,
)
from ai_poc_planner.persistence.errors import DatabaseOperationError


class SQLitePlanningReportRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_version(self, version_id: UUID) -> PersistedPlanningReport | None:
        row = self._connection.execute(
            "SELECT * FROM planning_reports WHERE version_id = ?", (str(version_id),)
        ).fetchone()
        if row is None:
            return None
        try:
            stored_report = json.loads(row["report_json"])
            synthesis = (
                stored_report.pop("synthesis", None)
                if isinstance(stored_report, dict)
                else None
            )
            return PersistedPlanningReport.model_validate(
                {
                    "id": row["id"],
                    "version_id": row["version_id"],
                    "analysis_id": row["analysis_id"],
                    "report": stored_report,
                    "markdown": row["markdown"],
                    "created_at": row["created_at"],
                    "synthesis": synthesis,
                }
            )
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise DatabaseOperationError("stored report is invalid") from error

    def create(self, report: PersistedPlanningReport) -> None:
        try:
            self._connection.execute(
                "INSERT INTO planning_reports (id, version_id, analysis_id, report_json, markdown, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(report.id),
                    str(report.version_id),
                    str(report.analysis_id),
                    json.dumps(
                        {
                            **report.report.model_dump(mode="json"),
                            "synthesis": report.synthesis.model_dump(mode="json")
                            if report.synthesis is not None
                            else None,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    report.markdown,
                    report.created_at.isoformat(),
                ),
            )
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to persist report") from error
