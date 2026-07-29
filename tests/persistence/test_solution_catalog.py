from __future__ import annotations

from ai_poc_planner.domain.case_centered import RecommendationCategory
from ai_poc_planner.persistence import database_connection, initialize_database
from ai_poc_planner.persistence.solution_catalog import SQLiteSolutionCatalogRepository


def test_catalog_migration_seeds_only_reviewed_runtime_content(tmp_path) -> None:
    connection = database_connection(tmp_path / "catalog.sqlite3")
    try:
        initialize_database(connection)
        catalog = SQLiteSolutionCatalogRepository(connection)

        solution = catalog.get_approved_solution_for_category(
            RecommendationCategory.GOVERNED_ASSISTIVE
        )
        assert solution is not None
        assert solution.solution_key == "permission_request_rules_and_human_approval"
        assert solution.display_name_zh == "權限申請標準化、規則檢查與人工核准"
        assert solution.review_status.value == "approved"

        approved_cases = catalog.list_approved_cases_for_solution(solution.solution_key)
        assert all(case.review_status.value == "approved" for case in approved_cases)
        assert all(case.source_url for case in approved_cases)
        assert all(
            solution.solution_key in case.applicable_solution_keys
            for case in approved_cases
        )
    finally:
        connection.close()


def test_catalog_never_returns_unapproved_solution_or_case(tmp_path) -> None:
    connection = database_connection(tmp_path / "catalog.sqlite3")
    try:
        initialize_database(connection)
        connection.execute(
            """
            INSERT INTO solution_patterns (
                solution_key, recommendation_category, display_name_zh,
                short_description_zh, detailed_description_zh, suitable_when_zh,
                not_suitable_when_zh, typical_scope_zh, human_boundary_zh,
                expected_outputs_zh, acceptance_focus_zh, review_status,
                content_version, created_at, updated_at
            ) VALUES (
                'pending-pattern', 'pending_category', '暫存方案', '暫存',
                '暫存', '暫存',
                '暫存', '暫存', '暫存', '暫存', '暫存', 'pending', 'test',
                '2026-07-28T00:00:00+00:00', '2026-07-28T00:00:00+00:00'
            )
            """
        )
        catalog = SQLiteSolutionCatalogRepository(connection)

        assert catalog.get_solution("pending-pattern") is None
        assert all(
            item.solution_key != "pending-pattern"
            for item in catalog.list_approved_solutions()
        )
    finally:
        connection.close()
