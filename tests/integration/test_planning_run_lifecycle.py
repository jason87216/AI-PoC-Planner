from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_poc_planner.application.contracts import OfflinePlanningResult
from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.planning_runs import PlanningRunService
from ai_poc_planner.application.planning_workflow import (
    run_and_persist_offline_planning,
)
from ai_poc_planner.application.workflow import run_offline_planning
from ai_poc_planner.domain.enums import PlanningRunStatus
from ai_poc_planner.domain.models import ClarifyingQuestion
from ai_poc_planner.domain.workflow import PlanningRun
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InvalidPlanningRunInputError,
    InvalidPlanningRunTransitionError,
    InvalidStoredPlanningRunError,
    PlanningRunAlreadyExistsError,
    PlanningRunNotFoundError,
    ProjectNotFoundError,
)
from ai_poc_planner.persistence.planning_runs import SQLitePlanningRunRepository
from ai_poc_planner.persistence.projects import SQLiteProjectRepository
from ai_poc_planner.persistence.schema import (
    CURRENT_SCHEMA_VERSION,
    initialize_database,
    read_schema_version,
)

PROJECT_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_PROJECT_ID = UUID("22222222-2222-4222-8222-222222222222")
RUN_ID = UUID("33333333-3333-4333-8333-333333333333")
MISSING_RUN_ID = UUID("99999999-9999-4999-8999-999999999999")
NOW = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=5)


def _question(field: str = "scenario") -> ClarifyingQuestion:
    return ClarifyingQuestion(
        field=field,
        question=f"Please provide {field}.",
        reason="Required for deterministic assessment.",
        priority=1,
    )


def _run_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": RUN_ID,
        "project_id": PROJECT_ID,
        "status": PlanningRunStatus.CREATED,
        "original_request": "我們公司想導入 AI 提升效率",
        "intent": {"summary": "導入 AI 提升效率"},
        "known_information": {},
        "missing_information": [],
        "clarifying_questions": [],
        "clarification_answers": {},
        "assessment": None,
        "proposal": None,
        "markdown_report": None,
        "error_code": None,
        "error_message": None,
        "created_at": NOW,
        "updated_at": NOW,
        "completed_at": None,
    }
    payload.update(overrides)
    return payload


def _project():
    return build_demo_request().project.model_copy(
        update={
            "id": PROJECT_ID,
            "created_at": NOW,
            "updated_at": NOW,
        }
    )


def _created_run(
    *,
    run_id: UUID = RUN_ID,
    project_id: UUID = PROJECT_ID,
    created_at: datetime = NOW,
) -> PlanningRun:
    return PlanningRun.model_validate(
        _run_payload(
            id=run_id,
            project_id=project_id,
            created_at=created_at,
            updated_at=created_at,
        )
    )


def _completed_run() -> tuple[OfflinePlanningResult, PlanningRun]:
    result = run_offline_planning(build_demo_request())
    run = PlanningRun.model_validate(
        _run_payload(
            project_id=result.project.id,
            status=PlanningRunStatus.COMPLETED,
            known_information=result.proposal.known_information,
            assessment=result.assessment,
            proposal=result.proposal,
            markdown_report=result.markdown,
            updated_at=LATER,
            completed_at=LATER,
        )
    )
    return result, run


def _repositories(
    path: Path,
) -> tuple[
    sqlite3.Connection,
    SQLiteProjectRepository,
    SQLitePlanningRunRepository,
]:
    connection = database_connection(path)
    initialize_database(connection)
    return (
        connection,
        SQLiteProjectRepository(connection),
        SQLitePlanningRunRepository(connection),
    )


def test_created_planning_run_has_only_in_progress_data() -> None:
    run = PlanningRun.model_validate(_run_payload())

    assert run.status is PlanningRunStatus.CREATED
    assert run.assessment is None
    assert run.completed_at is None


def test_clarification_required_needs_at_least_one_question() -> None:
    with pytest.raises(ValidationError, match="clarification_required"):
        PlanningRun.model_validate(
            _run_payload(status=PlanningRunStatus.CLARIFICATION_REQUIRED)
        )


def test_clarification_required_accepts_one_to_four_unique_questions() -> None:
    questions = [_question("scenario"), _question("owner")]

    run = PlanningRun.model_validate(
        _run_payload(
            status=PlanningRunStatus.CLARIFICATION_REQUIRED,
            missing_information=["scenario", "owner"],
            clarifying_questions=questions,
        )
    )

    assert run.clarifying_questions == questions


def test_completed_run_requires_assessment_proposal_report_and_timestamp() -> None:
    with pytest.raises(ValidationError, match="completed"):
        PlanningRun.model_validate(
            _run_payload(status=PlanningRunStatus.COMPLETED, updated_at=LATER)
        )


def test_completed_run_accepts_one_consistent_offline_result() -> None:
    result = run_offline_planning(build_demo_request())

    run = PlanningRun.model_validate(
        _run_payload(
            project_id=result.project.id,
            status=PlanningRunStatus.COMPLETED,
            known_information=result.proposal.known_information,
            assessment=result.assessment,
            proposal=result.proposal,
            markdown_report=result.markdown,
            updated_at=LATER,
            completed_at=LATER,
        )
    )

    assert run.assessment == result.assessment
    assert run.proposal == result.proposal
    assert run.markdown_report == result.markdown


def test_failed_run_requires_stable_error_code_and_safe_message() -> None:
    with pytest.raises(ValidationError, match="failed"):
        PlanningRun.model_validate(
            _run_payload(status=PlanningRunStatus.FAILED, updated_at=LATER)
        )


def test_non_completed_run_rejects_formal_result_payload() -> None:
    result = run_offline_planning(build_demo_request())

    with pytest.raises(ValidationError, match="non-completed"):
        PlanningRun.model_validate(
            _run_payload(
                assessment=result.assessment,
                proposal=result.proposal,
                markdown_report=result.markdown,
            )
        )


def test_run_rejects_unknown_status_and_invalid_timestamp_order() -> None:
    with pytest.raises(ValidationError):
        PlanningRun.model_validate(_run_payload(status="waiting"))

    with pytest.raises(ValidationError, match="updated_at"):
        PlanningRun.model_validate(_run_payload(updated_at=NOW - timedelta(seconds=1)))


def test_fresh_database_initializes_planning_run_schema_at_current_version(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    try:
        initialize_database(connection)

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(planning_runs)")
        }
        assert read_schema_version(connection) == CURRENT_SCHEMA_VERSION == 3
        assert {
            "id",
            "project_id",
            "status",
            "original_request",
            "intent_json",
            "known_information_json",
            "missing_information_json",
            "clarifying_questions_json",
            "clarification_answers_json",
            "assessment_json",
            "proposal_json",
            "markdown_report",
            "error_code",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
        } == columns
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(planning_runs)"
        ).fetchall()
        assert [(row["table"], row["from"], row["to"]) for row in foreign_keys] == [
            ("analysis_projects", "project_id", "id")
        ]
    finally:
        connection.close()


def test_version_one_database_upgrades_to_current_and_preserves_project(
    tmp_path: Path,
) -> None:
    connection = database_connection(tmp_path / "planner.sqlite3")
    try:
        connection.execute(
            """
            CREATE TABLE analysis_projects (
                id TEXT PRIMARY KEY NOT NULL,
                title TEXT NOT NULL,
                problem_statement TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
        SQLiteProjectRepository(connection).create(_project())

        initialize_database(connection)

        assert read_schema_version(connection) == CURRENT_SCHEMA_VERSION == 3
        assert SQLiteProjectRepository(connection).get(PROJECT_ID) == _project()
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = ?",
                ("planning_runs",),
            ).fetchone()[0]
            == "planning_runs"
        )
    finally:
        connection.close()


def test_database_initialization_is_idempotent_with_planning_run_data(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    try:
        projects.create(_project())
        runs.create(_created_run())

        initialize_database(connection)

        assert runs.get(RUN_ID) == _created_run()
    finally:
        connection.close()


def test_planning_run_create_and_load_round_trip_every_field(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    result, completed = _completed_run()
    try:
        projects.create(result.project)

        created = runs.create(completed)
        loaded = runs.get(RUN_ID)

        assert created == completed
        assert loaded == completed
        assert loaded.model_dump(mode="json") == completed.model_dump(mode="json")
    finally:
        connection.close()


def test_planning_run_foreign_key_failure_has_stable_project_error(
    tmp_path: Path,
) -> None:
    connection, _, runs = _repositories(tmp_path / "planner.sqlite3")
    try:
        with pytest.raises(ProjectNotFoundError) as error:
            runs.create(_created_run())

        assert error.value.code == "project_not_found"
    finally:
        connection.close()


def test_duplicate_planning_run_raises_stable_error(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    try:
        projects.create(_project())
        runs.create(_created_run())

        with pytest.raises(PlanningRunAlreadyExistsError) as error:
            runs.create(_created_run())

        assert error.value.code == "planning_run_already_exists"
    finally:
        connection.close()


def test_missing_planning_run_raises_stable_error(tmp_path: Path) -> None:
    connection, _, runs = _repositories(tmp_path / "planner.sqlite3")
    try:
        with pytest.raises(PlanningRunNotFoundError) as error:
            runs.get(MISSING_RUN_ID)

        assert error.value.code == "planning_run_not_found"
    finally:
        connection.close()


def test_corrupt_json_is_rejected_when_loading_planning_run(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    try:
        projects.create(_project())
        runs.create(_created_run())
        connection.execute(
            "UPDATE planning_runs SET intent_json = ? WHERE id = ?",
            ("{not-json", str(RUN_ID)),
        )
        connection.commit()

        with pytest.raises(InvalidStoredPlanningRunError) as error:
            runs.get(RUN_ID)

        assert error.value.code == "invalid_stored_planning_run"
    finally:
        connection.close()


def test_corrupt_nested_assessment_is_rejected_on_load(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    result, completed = _completed_run()
    try:
        projects.create(result.project)
        runs.create(completed)
        connection.execute(
            "UPDATE planning_runs SET assessment_json = ? WHERE id = ?",
            ('{"schema_version":"1.0"}', str(RUN_ID)),
        )
        connection.commit()

        with pytest.raises(InvalidStoredPlanningRunError):
            runs.get(RUN_ID)
    finally:
        connection.close()


def test_planning_run_update_round_trips_clarification_state(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    questions = [_question("scenario"), _question("owner")]
    clarification = PlanningRun.model_validate(
        _run_payload(
            status=PlanningRunStatus.CLARIFICATION_REQUIRED,
            missing_information=["scenario", "owner"],
            clarifying_questions=questions,
            updated_at=LATER,
        )
    )
    try:
        projects.create(_project())
        runs.create(_created_run())

        assert runs.update(clarification) == clarification
        assert runs.get(RUN_ID) == clarification
    finally:
        connection.close()


def test_failed_update_rolls_back_and_preserves_prior_run(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    updated = _created_run().model_copy(
        update={"original_request": "Changed", "updated_at": LATER}
    )
    try:
        projects.create(_project())
        original = runs.create(_created_run())
        connection.execute(
            """
            CREATE TRIGGER reject_run_update
            BEFORE UPDATE ON planning_runs
            BEGIN
                SELECT RAISE(ABORT, 'rejected by test trigger');
            END
            """
        )
        connection.commit()

        with pytest.raises(DatabaseOperationError):
            runs.update(updated)

        assert runs.get(RUN_ID) == original
        assert connection.in_transaction is False
    finally:
        connection.close()


def test_list_for_project_is_newest_first_and_isolated(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    second_run_id = UUID("44444444-4444-4444-8444-444444444444")
    other_run_id = UUID("55555555-5555-4555-8555-555555555555")
    try:
        projects.create(_project())
        projects.create(_project().model_copy(update={"id": OTHER_PROJECT_ID}))
        runs.create(_created_run())
        runs.create(_created_run(run_id=second_run_id, created_at=LATER))
        runs.create(_created_run(run_id=other_run_id, project_id=OTHER_PROJECT_ID))

        assert [run.id for run in runs.list_for_project(PROJECT_ID)] == [
            second_run_id,
            RUN_ID,
        ]
        assert [run.id for run in runs.list_for_project(OTHER_PROJECT_ID)] == [
            other_run_id
        ]
    finally:
        connection.close()


def test_sql_values_are_parameterized_and_input_is_not_mutated(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    malicious = _created_run().model_copy(
        update={"original_request": "x'); DROP TABLE planning_runs; --"}
    )
    before = malicious.model_dump(mode="json")
    try:
        projects.create(_project())

        runs.create(malicious)

        assert runs.get(RUN_ID).original_request == malicious.original_request
        assert malicious.model_dump(mode="json") == before
        assert (
            connection.execute("SELECT COUNT(*) FROM planning_runs").fetchone()[0] == 1
        )
    finally:
        connection.close()


def test_service_creates_and_lists_run_with_fixed_uuid_and_clock(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(
        runs,
        projects,
        uuid_factory=lambda: RUN_ID,
        clock=lambda: NOW,
    )
    try:
        projects.create(_project())

        created = service.create(
            project_id=PROJECT_ID,
            original_request="我們公司想導入 AI 提升效率",
        )

        assert created == _created_run().model_copy(
            update={"intent": {"summary": "我們公司想導入 AI 提升效率"}}
        )
        assert created.intent == {"summary": "我們公司想導入 AI 提升效率"}
        assert service.list_for_project(PROJECT_ID) == [created]
    finally:
        connection.close()


def test_service_rejects_run_for_missing_project(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects)
    try:
        with pytest.raises(ProjectNotFoundError):
            service.create(
                project_id=PROJECT_ID,
                original_request="Missing project",
            )
    finally:
        connection.close()


def test_service_rejects_empty_clarification_question_set(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    try:
        projects.create(_project())
        runs.create(_created_run())

        with pytest.raises(InvalidPlanningRunInputError):
            service.require_clarification(
                RUN_ID,
                intent={"summary": "AI efficiency"},
                known_information={},
                questions=[],
            )
    finally:
        connection.close()


def test_service_rejects_invalid_status_transition(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    try:
        projects.create(_project())
        runs.create(_created_run())

        with pytest.raises(InvalidPlanningRunTransitionError) as error:
            service.submit_clarification(RUN_ID, {"owner": "流程負責人"})

        assert error.value.code == "invalid_planning_run_transition"
    finally:
        connection.close()


def test_submit_clarification_persists_answers_and_returns_to_created(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    questions = [_question("scenario"), _question("owner")]
    clarification = PlanningRun.model_validate(
        _run_payload(
            status=PlanningRunStatus.CLARIFICATION_REQUIRED,
            missing_information=["scenario", "owner"],
            clarifying_questions=questions,
        )
    )
    answers = {"scenario": "high_value_low_risk", "owner": "流程負責人"}
    try:
        projects.create(_project())
        runs.create(clarification)

        updated = service.submit_clarification(RUN_ID, answers)

        assert updated.status is PlanningRunStatus.CREATED
        assert updated.clarification_answers == answers
        assert updated.known_information == answers
        assert updated.clarifying_questions == questions
        assert updated.missing_information == []
        assert runs.get(RUN_ID) == updated
    finally:
        connection.close()


def test_service_complete_persists_exact_formal_result_and_utc_time(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    result, _ = _completed_run()
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    try:
        projects.create(result.project)
        runs.create(_created_run(project_id=result.project.id))

        completed = service.complete(
            RUN_ID,
            assessment=result.assessment,
            proposal=result.proposal,
            markdown_report=result.markdown,
        )

        assert completed.status is PlanningRunStatus.COMPLETED
        assert completed.assessment == result.assessment
        assert completed.proposal == result.proposal
        assert completed.markdown_report == result.markdown
        assert completed.completed_at == LATER
        assert completed.completed_at.tzinfo is UTC
    finally:
        connection.close()


def test_service_fail_persists_stable_error(tmp_path: Path) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    try:
        projects.create(_project())
        runs.create(_created_run())

        failed = service.fail(
            RUN_ID,
            error_code="provider_error",
            error_message="Offline planning could not complete.",
        )

        assert failed.status is PlanningRunStatus.FAILED
        assert failed.error_code == "provider_error"
        assert failed.error_message == "Offline planning could not complete."
        assert runs.get(RUN_ID) == failed
    finally:
        connection.close()


def test_persisted_clarification_to_completed_scenario_is_offline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    times = iter([NOW, NOW + timedelta(minutes=1), LATER, LATER + timedelta(minutes=1)])
    service = PlanningRunService(
        runs,
        projects,
        uuid_factory=lambda: RUN_ID,
        clock=lambda: next(times),
    )

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("persisted fake-model scenario must remain offline")

    monkeypatch.setattr("socket.create_connection", fail_network)
    try:
        project = projects.create(_project())
        created = service.create(
            project_id=project.id,
            original_request="我們公司想導入 AI 提升效率",
        )

        clarification = run_and_persist_offline_planning(
            created.id,
            service=service,
            project_reader=projects,
        )
        assert clarification.status is PlanningRunStatus.CLARIFICATION_REQUIRED
        assert [question.field for question in clarification.clarifying_questions] == [
            "target_users",
            "current_workflow",
            "data_sources",
            "owner",
        ]

        service.submit_clarification(
            created.id,
            {
                "target_users": ["營運團隊"],
                "current_workflow": "人工整理重複需求。",
                "data_sources": ["核准流程文件", "代表性樣本"],
                "owner": "營運流程負責人",
            },
        )
        completed = run_and_persist_offline_planning(
            created.id,
            service=service,
            project_reader=projects,
        )
        reloaded = runs.get(created.id)

        assert completed.status is PlanningRunStatus.COMPLETED
        assert reloaded == completed
        assert reloaded.assessment is not None
        assert reloaded.proposal is not None
        assert reloaded.markdown_report is not None
        assert reloaded.assessment.weighted_score == reloaded.proposal.weighted_score
        assert (
            reloaded.assessment.gate_disposition is reloaded.proposal.gate_disposition
        )
        assert reloaded.assessment.recommendation is reloaded.proposal.recommendation
    finally:
        connection.close()


def test_coordinator_persists_known_workflow_failure_as_failed(
    tmp_path: Path,
) -> None:
    connection, projects, runs = _repositories(tmp_path / "planner.sqlite3")
    service = PlanningRunService(runs, projects, clock=lambda: LATER)
    try:
        projects.create(_project())
        runs.create(
            PlanningRun.model_validate(
                _run_payload(known_information={"simulate_provider_error": True})
            )
        )

        failed = run_and_persist_offline_planning(
            RUN_ID,
            service=service,
            project_reader=projects,
        )

        assert failed.status is PlanningRunStatus.FAILED
        assert failed.error_code == "provider_error"
        assert failed.error_message == "Offline planning could not complete."
    finally:
        connection.close()
