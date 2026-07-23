from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.projects import AnalysisProjectService
from ai_poc_planner.application.workflow import run_offline_planning
from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidProjectInputError,
    InvalidStoredProjectError,
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.schema import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    read_schema_version,
)

PROJECT_ID = UUID("11111111-1111-4111-8111-111111111111")
MISSING_PROJECT_ID = UUID("99999999-9999-4999-8999-999999999999")
NOW = datetime(2026, 7, 20, 8, 30, 45, 123456, tzinfo=UTC)


def _project(
    *,
    project_id: UUID = PROJECT_ID,
    title: str = "客服知識檢索 PoC",
    status: ProjectStatus = ProjectStatus.DRAFT,
    created_at: datetime = NOW,
    updated_at: datetime = NOW,
) -> AnalysisProject:
    return AnalysisProject(
        id=project_id,
        title=title,
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=status,
        created_at=created_at,
        updated_at=updated_at,
    )


def _repository(path: Path) -> tuple[sqlite3.Connection, SQLiteProjectRepository]:
    connection = database_connection(path)
    initialize_database(connection)
    return connection, SQLiteProjectRepository(connection)


def _insert_raw_project(
    connection: sqlite3.Connection,
    *,
    status: str = "draft",
    created_at: str = "2026-07-20T08:30:45.123456+00:00",
    updated_at: str = "2026-07-20T08:30:45.123456+00:00",
) -> None:
    connection.execute(
        """
        INSERT INTO analysis_projects (
            id, title, problem_statement, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(PROJECT_ID),
            "Raw project",
            "Stored row used to exercise validation.",
            status,
            created_at,
            updated_at,
        ),
    )
    connection.commit()


def test_database_initialization_creates_current_schema(tmp_path: Path) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    try:
        initialize_database(connection)

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(analysis_projects)")
        }
        assert columns == {
            "id",
            "title",
            "problem_statement",
            "status",
            "created_at",
            "updated_at",
        }
        assert read_schema_version(connection) == CURRENT_SCHEMA_VERSION == 3
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_database_initialization_is_idempotent_and_preserves_data(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        repository.create(_project())
        initialize_database(connection)

        assert repository.get(PROJECT_ID) == _project()
    finally:
        connection.close()


def test_service_creates_project_with_injected_uuid_and_clock(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    service = AnalysisProjectService(
        repository,
        uuid_factory=lambda: PROJECT_ID,
        clock=lambda: NOW,
    )
    try:
        created = service.create(
            title="客服知識檢索 PoC",
            problem_statement="客服需要更快找到已核准的產品答案。",
        )

        assert created == _project()
        assert created.created_at == created.updated_at
    finally:
        connection.close()


def test_service_loads_project_through_repository_boundary(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    service = AnalysisProjectService(repository)
    try:
        repository.create(_project())

        assert service.load(PROJECT_ID) == _project()
    finally:
        connection.close()


def test_service_maps_invalid_creation_input_to_stable_error(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    service = AnalysisProjectService(
        repository,
        uuid_factory=lambda: PROJECT_ID,
        clock=lambda: NOW,
    )
    try:
        with pytest.raises(InvalidProjectInputError) as error:
            service.create(title="", problem_statement="Valid problem statement")

        assert error.value.code == "invalid_project_input"
    finally:
        connection.close()


def test_repository_loads_project_by_uuid(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        repository.create(_project())

        assert repository.get(PROJECT_ID).id == PROJECT_ID
    finally:
        connection.close()


def test_create_then_load_round_trips_every_contract_field(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    project = _project(
        status=ProjectStatus.CLARIFICATION_REQUIRED,
        updated_at=NOW + timedelta(hours=2),
    )
    try:
        created = repository.create(project)
        loaded = repository.get(project.id)

        assert created == project
        assert loaded == project
        assert loaded.model_dump(mode="json") == project.model_dump(mode="json")
    finally:
        connection.close()


def test_title_problem_and_enum_value_are_saved_in_separate_columns(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    project = _project(status=ProjectStatus.INTERVIEWING)
    try:
        repository.create(project)

        row = connection.execute(
            "SELECT title, problem_statement, status "
            "FROM analysis_projects WHERE id = ?",
            (str(PROJECT_ID),),
        ).fetchone()
        assert tuple(row) == (
            project.title,
            project.problem_statement,
            ProjectStatus.INTERVIEWING.value,
        )
    finally:
        connection.close()


def test_timestamps_round_trip_as_timezone_aware_utc(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    source_time = datetime(
        2026,
        7,
        20,
        16,
        30,
        45,
        123456,
        tzinfo=timezone(timedelta(hours=8)),
    )
    project = _project(created_at=source_time, updated_at=source_time)
    try:
        repository.create(project)
        loaded = repository.get(PROJECT_ID)

        assert loaded.created_at == NOW
        assert loaded.updated_at == NOW
        assert loaded.created_at.tzinfo is UTC
        stored = connection.execute(
            "SELECT created_at FROM analysis_projects WHERE id = ?",
            (str(PROJECT_ID),),
        ).fetchone()[0]
        assert stored == "2026-07-20T08:30:45.123456+00:00"
    finally:
        connection.close()


def test_duplicate_project_id_raises_stable_error(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        repository.create(_project())

        with pytest.raises(ProjectAlreadyExistsError) as error:
            repository.create(_project(title="Different title"))

        assert error.value.code == "project_already_exists"
        assert repository.get(PROJECT_ID).title == "客服知識檢索 PoC"
    finally:
        connection.close()


def test_missing_project_raises_stable_error(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        with pytest.raises(ProjectNotFoundError) as error:
            repository.get(MISSING_PROJECT_ID)

        assert error.value.code == "project_not_found"
    finally:
        connection.close()


def test_invalid_project_id_input_is_rejected(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        with pytest.raises(InvalidProjectInputError) as error:
            repository.get(cast(UUID, "not-a-uuid"))

        assert error.value.code == "invalid_project_input"
    finally:
        connection.close()


def test_invalid_project_model_input_is_revalidated(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    invalid = AnalysisProject.model_construct(
        id=PROJECT_ID,
        title="",
        problem_statement="Valid problem statement",
        status=ProjectStatus.DRAFT,
        created_at=NOW,
        updated_at=NOW,
    )
    try:
        with pytest.raises(InvalidProjectInputError) as error:
            repository.create(invalid)

        assert error.value.code == "invalid_project_input"
    finally:
        connection.close()


def test_invalid_persisted_enum_is_reported_as_corrupt_data(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        _insert_raw_project(connection, status="unknown-status")

        with pytest.raises(InvalidStoredProjectError) as error:
            repository.get(PROJECT_ID)

        assert error.value.code == "invalid_stored_project"
    finally:
        connection.close()


def test_invalid_persisted_datetime_is_reported_as_corrupt_data(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        _insert_raw_project(connection, created_at="not-a-datetime")

        with pytest.raises(InvalidStoredProjectError) as error:
            repository.get(PROJECT_ID)

        assert error.value.code == "invalid_stored_project"
    finally:
        connection.close()


@pytest.mark.parametrize("schema_version", [0, CURRENT_SCHEMA_VERSION])
def test_incompatible_table_shape_has_clear_schema_error(
    tmp_path: Path,
    schema_version: int,
) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    try:
        connection.execute("CREATE TABLE analysis_projects (id TEXT PRIMARY KEY)")
        connection.execute(f"PRAGMA user_version = {schema_version}")
        connection.commit()

        with pytest.raises(SchemaMismatchError) as error:
            initialize_database(connection)

        assert error.value.code == "schema_mismatch"
    finally:
        connection.close()


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    try:
        connection.execute("PRAGMA user_version = 99")

        with pytest.raises(UnsupportedSchemaVersionError) as error:
            initialize_database(connection)

        assert error.value.code == "unsupported_schema_version"
    finally:
        connection.close()


def test_project_values_are_parameterized_not_interpreted_as_sql(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    title = "x'); DROP TABLE analysis_projects; --"
    try:
        repository.create(_project(title=title))

        assert repository.get(PROJECT_ID).title == title
        assert (
            connection.execute("SELECT COUNT(*) FROM analysis_projects").fetchone()[0]
            == 1
        )
    finally:
        connection.close()


def test_failed_create_rolls_back_and_keeps_connection_usable(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    try:
        connection.execute(
            """
            CREATE TRIGGER reject_project
            BEFORE INSERT ON analysis_projects
            BEGIN
                SELECT RAISE(ABORT, 'rejected by test trigger');
            END
            """
        )
        connection.commit()

        with pytest.raises(DatabaseOperationError) as error:
            repository.create(_project())

        assert error.value.code == "database_operation_failed"
        assert (
            connection.execute("SELECT COUNT(*) FROM analysis_projects").fetchone()[0]
            == 0
        )
        assert connection.in_transaction is False
    finally:
        connection.close()


def test_repository_does_not_modify_input_model(tmp_path: Path) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    project = _project()
    before = project.model_dump(mode="json")
    try:
        repository.create(project)

        assert project.model_dump(mode="json") == before
    finally:
        connection.close()


def test_temporary_databases_are_isolated(tmp_path: Path) -> None:
    first_connection, first = _repository(tmp_path / "first.sqlite3")
    second_connection, second = _repository(tmp_path / "second.sqlite3")
    try:
        first.create(_project())

        assert first.get(PROJECT_ID) == _project()
        with pytest.raises(ProjectNotFoundError):
            second.get(PROJECT_ID)
    finally:
        first_connection.close()
        second_connection.close()


def test_database_connection_can_be_closed_cleanly(tmp_path: Path) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    initialize_database(connection)

    connection.close()

    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")


def test_closed_connection_is_mapped_to_stable_database_error(
    tmp_path: Path,
) -> None:
    connection, repository = _repository(tmp_path / "planner.sqlite3")
    connection.close()

    with pytest.raises(DatabaseOperationError) as error:
        repository.get(PROJECT_ID)

    assert error.value.code == "database_operation_failed"


def test_existing_offline_demo_remains_in_memory_and_deterministic() -> None:
    request = build_demo_request()

    first = run_offline_planning(request)
    second = run_offline_planning(request)

    assert first == second
    assert first.project == request.project
