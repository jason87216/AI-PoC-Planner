from __future__ import annotations

import sqlite3

import pytest

from ai_poc_planner.persistence.errors import (
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)
from ai_poc_planner.persistence.schema import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
)


def test_fresh_database_creates_v6_analysis_and_report_tables() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_database(connection)

    assert CURRENT_SCHEMA_VERSION == 6
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 6
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {
        "planning_analysis_results",
        "planning_analysis_options",
        "planning_analysis_scores",
        "planning_analysis_fact_references",
        "planning_analysis_gate_results",
        "planning_reports",
    } <= tables


def test_v4_database_additively_upgrades_to_v6() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_database(connection)
    connection.execute("DROP TABLE planning_analysis_gate_results")
    connection.execute("PRAGMA user_version = 4")
    connection.commit()

    initialize_database(connection)

    assert connection.execute("PRAGMA user_version").fetchone()[0] == 6


def test_future_and_incomplete_schema_are_rejected() -> None:
    future = sqlite3.connect(":memory:")
    future.execute("PRAGMA user_version = 99")
    with pytest.raises(UnsupportedSchemaVersionError):
        initialize_database(future)

    incomplete = sqlite3.connect(":memory:")
    initialize_database(incomplete)
    incomplete.execute("DROP TABLE planning_analysis_scores")
    with pytest.raises(SchemaMismatchError):
        initialize_database(incomplete)
