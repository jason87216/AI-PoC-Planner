from __future__ import annotations

import pytest

from ai_poc_planner.persistence import database_connection, initialize_database
from ai_poc_planner.persistence.solution_catalog import (
    CatalogCoverageError,
    SQLiteSolutionCatalogRepository,
)


def test_permission_catalog_has_many_to_many_links_and_coverage(tmp_path) -> None:
    connection = database_connection(tmp_path / "catalog.sqlite3")
    try:
        initialize_database(connection)
        catalog = SQLiteSolutionCatalogRepository(connection)

        solution_key = "permission_request_rules_and_human_approval"
        links = catalog.list_approved_case_links_for_solution(solution_key)
        assert {link.support_type for link in links} >= {"primary", "supporting"}
        assert all(link.review_status.value == "approved" for link in links)
        assert all(link.supported_practice_keys for link in links)
        assert all(
            case.case_id in {link.case_id for link in links}
            for case in catalog.list_approved_cases_for_solution(solution_key)
        )

        references = catalog.list_approved_implementation_references(solution_key)
        assert references
        assert all(reference.source_url for reference in references)

        coverage = catalog.get_golden_coverage("governed_access")
        assert coverage is not None
        assert coverage.expected_solution_key == solution_key
        assert coverage.minimum_primary_cases == 1
        assert coverage.minimum_supporting_cases == 1
        assert coverage.minimum_implementation_references == 1
    finally:
        connection.close()


def test_catalog_coverage_fails_closed_when_required_evidence_is_missing(
    tmp_path,
) -> None:
    connection = database_connection(tmp_path / "catalog.sqlite3")
    try:
        initialize_database(connection)
        catalog = SQLiteSolutionCatalogRepository(connection)

        with pytest.raises(CatalogCoverageError, match="CATALOG_COVERAGE_ERROR"):
            catalog.require_coverage(
                "governed_access",
                "permission_request_rules_and_human_approval",
                matched_case_ids=[],
            )
    finally:
        connection.close()
