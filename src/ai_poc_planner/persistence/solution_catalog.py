"""Read-only access to reviewed solution and case content in SQLite."""

from __future__ import annotations

import sqlite3

from ai_poc_planner.domain.case_centered import RecommendationCategory
from ai_poc_planner.domain.reviewed_cases import ReviewedCase
from ai_poc_planner.domain.solution_catalog import SolutionPattern


class ReviewedCatalogueError(RuntimeError):
    """Approved catalogue data is incomplete or cannot be used safely."""


class SQLiteSolutionCatalogRepository:
    """The runtime source of truth for approved reader-facing catalogue content."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_solution(self, solution_key: str) -> SolutionPattern | None:
        row = self._connection.execute(
            """
            SELECT * FROM solution_patterns
            WHERE solution_key = ? AND review_status = 'approved'
            """,
            (solution_key,),
        ).fetchone()
        return None if row is None else self._solution_from_row(row)

    def get_approved_solution_for_category(
        self, category: RecommendationCategory | str
    ) -> SolutionPattern | None:
        row = self._connection.execute(
            """
            SELECT * FROM solution_patterns
            WHERE recommendation_category = ? AND review_status = 'approved'
            ORDER BY solution_key
            LIMIT 1
            """,
            (getattr(category, "value", category),),
        ).fetchone()
        return None if row is None else self._solution_from_row(row)

    def list_approved_solutions(self) -> tuple[SolutionPattern, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM solution_patterns
            WHERE review_status = 'approved'
            ORDER BY solution_key
            """
        ).fetchall()
        return tuple(self._solution_from_row(row) for row in rows)

    def get_approved_case(self, case_id: str) -> ReviewedCase | None:
        row = self._connection.execute(
            """
            SELECT payload_json FROM reviewed_cases
            WHERE case_id = ? AND review_status = 'approved'
            """,
            (case_id,),
        ).fetchone()
        return None if row is None else self._case_from_row(row)

    def list_approved_cases_for_solution(
        self, solution_key: str
    ) -> tuple[ReviewedCase, ...]:
        rows = self._connection.execute(
            """
            SELECT payload_json FROM reviewed_cases
            WHERE review_status = 'approved'
            ORDER BY case_id
            """
        ).fetchall()
        cases = tuple(self._case_from_row(row) for row in rows)
        return tuple(
            case for case in cases if solution_key in case.applicable_solution_keys
        )

    @staticmethod
    def _solution_from_row(row: sqlite3.Row) -> SolutionPattern:
        return SolutionPattern.model_validate(dict(row))

    @staticmethod
    def _case_from_row(row: sqlite3.Row) -> ReviewedCase:
        case = ReviewedCase.model_validate_json(row["payload_json"])
        required = (
            case.display_title_zh,
            case.case_summary_zh,
            case.problem_context_zh,
            case.implemented_approach_zh,
            case.documented_outcomes_zh,
            case.transferable_practices_zh,
            case.limitations_zh,
            case.reviewed_at,
            case.content_version,
        )
        if (
            case.review_status.value != "approved"
            or not case.source_url
            or not case.applicable_solution_keys
            or any(value is None for value in required)
        ):
            raise ReviewedCatalogueError("approved reviewed case is incomplete")
        return case
