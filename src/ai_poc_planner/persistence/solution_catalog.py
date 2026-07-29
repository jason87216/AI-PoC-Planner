"""Read-only access to reviewed solution and case content in SQLite."""

from __future__ import annotations

import json
import sqlite3

from ai_poc_planner.domain.case_centered import RecommendationCategory
from ai_poc_planner.domain.catalog_relationships import (
    GoldenScenarioCoverage,
    ReviewedImplementationReference,
    SolutionCaseLink,
)
from ai_poc_planner.domain.reviewed_cases import ReviewedCase
from ai_poc_planner.domain.solution_catalog import SolutionPattern


class ReviewedCatalogueError(RuntimeError):
    """Approved catalogue data is incomplete or cannot be used safely."""


class CatalogCoverageError(ReviewedCatalogueError):
    """The formal scenario lacks the minimum reviewed evidence to report."""

    code = "CATALOG_COVERAGE_ERROR"


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
        category_value = getattr(category, "value", category)
        if category_value == RecommendationCategory.GOVERNED_ASSISTIVE.value:
            row = self._connection.execute(
                """
                SELECT * FROM solution_patterns
                WHERE solution_key = 'permission_request_rules_and_human_approval'
                  AND review_status = 'approved'
                LIMIT 1
                """
            ).fetchone()
            if row is not None:
                return self._solution_from_row(row)
        row = self._connection.execute(
            """
            SELECT * FROM solution_patterns
            WHERE recommendation_category = ? AND review_status = 'approved'
            ORDER BY CASE
                WHEN solution_key = 'rules_and_human_approval' THEN 0
                ELSE 1
            END,
                     solution_key
            LIMIT 1
            """,
            (category_value,),
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
            SELECT c.payload_json
            FROM reviewed_cases AS c
            JOIN solution_case_links AS l ON l.case_id = c.case_id
            WHERE c.review_status = 'approved'
              AND l.solution_key = ?
              AND l.review_status = 'approved'
              AND l.support_type IN ('primary', 'supporting')
            ORDER BY CASE l.support_type WHEN 'primary' THEN 0 ELSE 1 END, c.case_id
            """,
            (solution_key,),
        ).fetchall()
        return tuple(self._case_from_row(row) for row in rows)

    def list_approved_case_links_for_solution(
        self, solution_key: str
    ) -> tuple[SolutionCaseLink, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM solution_case_links
            WHERE solution_key = ? AND review_status = 'approved'
            ORDER BY CASE support_type WHEN 'primary' THEN 0
                                      WHEN 'supporting' THEN 1 ELSE 2 END, case_id
            """,
            (solution_key,),
        ).fetchall()
        return tuple(self._link_from_row(row) for row in rows)

    def list_approved_implementation_references(
        self, solution_key: str | None = None
    ) -> tuple[ReviewedImplementationReference, ...]:
        del solution_key  # references are filtered by approved practice coverage
        rows = self._connection.execute(
            """
            SELECT * FROM reviewed_implementation_references
            WHERE review_status = 'approved'
            ORDER BY reference_key
            """
        ).fetchall()
        return tuple(self._reference_from_row(row) for row in rows)

    def get_golden_coverage(self, scenario_id: str) -> GoldenScenarioCoverage | None:
        row = self._connection.execute(
            """
            SELECT * FROM golden_scenario_coverage WHERE scenario_id = ?
            """,
            (scenario_id,),
        ).fetchone()
        if row is None:
            return None
        return GoldenScenarioCoverage(
            scenario_id=row["scenario_id"],
            expected_solution_key=row["expected_solution_key"],
            required_practice_keys=json.loads(row["required_practice_keys_json"]),
            minimum_primary_cases=row["minimum_primary_cases"],
            minimum_supporting_cases=row["minimum_supporting_cases"],
            minimum_implementation_references=row["minimum_implementation_references"],
            content_version=row["content_version"],
        )

    def require_coverage(
        self,
        scenario_id: str,
        solution_key: str,
        *,
        matched_case_ids: list[str] | tuple[str, ...],
    ) -> None:
        coverage = self.get_golden_coverage(scenario_id)
        if coverage is None or coverage.expected_solution_key != solution_key:
            return
        links = [
            link
            for link in self.list_approved_case_links_for_solution(solution_key)
            if link.case_id in set(matched_case_ids)
        ]
        primary = sum(link.support_type == "primary" for link in links)
        supporting = sum(link.support_type == "supporting" for link in links)
        references = len(self.list_approved_implementation_references(solution_key))
        practice_keys = {key for link in links for key in link.supported_practice_keys}
        missing_practices = set(coverage.required_practice_keys) - practice_keys
        if (
            primary < coverage.minimum_primary_cases
            or supporting < coverage.minimum_supporting_cases
            or references < coverage.minimum_implementation_references
            or missing_practices
        ):
            raise CatalogCoverageError(
                "CATALOG_COVERAGE_ERROR: "
                f"{scenario_id} needs primary={coverage.minimum_primary_cases}, "
                f"supporting={coverage.minimum_supporting_cases}, "
                "implementation_references="
                f"{coverage.minimum_implementation_references}; "
                f"matched primary={primary}, supporting={supporting}, "
                f"references={references}, "
                f"missing practices={sorted(missing_practices)}"
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

    @staticmethod
    def _link_from_row(row: sqlite3.Row) -> SolutionCaseLink:
        return SolutionCaseLink(
            solution_key=row["solution_key"],
            case_id=row["case_id"],
            support_type=row["support_type"],
            supported_practice_keys=json.loads(row["supported_practice_keys_json"]),
            applicability_note_zh=row["applicability_note_zh"],
            limitation_note_zh=row["limitation_note_zh"],
            review_status=row["review_status"],
            content_version=row["content_version"],
        )

    @staticmethod
    def _reference_from_row(row: sqlite3.Row) -> ReviewedImplementationReference:
        return ReviewedImplementationReference(
            reference_key=row["reference_key"],
            display_title_zh=row["display_title_zh"],
            publisher=row["publisher"],
            summary_zh=row["summary_zh"],
            supported_practice_keys=json.loads(row["supported_practice_keys_json"]),
            source_name=row["source_name"],
            source_url=row["source_url"],
            review_status=row["review_status"],
            content_version=row["content_version"],
        )
