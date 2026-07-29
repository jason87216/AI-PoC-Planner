"""Explicit SQLite schema initialization with additive legacy-safe migrations."""

# ruff: noqa: E501

from __future__ import annotations

import json
import sqlite3

from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    SchemaMismatchError,
    UnsupportedSchemaVersionError,
)

CURRENT_SCHEMA_VERSION = 8
_PROJECT_COLUMNS = frozenset(
    {
        "id",
        "title",
        "problem_statement",
        "status",
        "created_at",
        "updated_at",
    }
)
_CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_projects (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL,
    problem_statement TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_PLANNING_RUN_COLUMNS = frozenset(
    {
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
    }
)
_CREATE_PLANNING_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_runs (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES analysis_projects(id),
    status TEXT NOT NULL,
    original_request TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    known_information_json TEXT NOT NULL,
    missing_information_json TEXT NOT NULL,
    clarifying_questions_json TEXT NOT NULL,
    clarification_answers_json TEXT NOT NULL,
    assessment_json TEXT,
    proposal_json TEXT,
    markdown_report TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
)
"""
_CREATE_PLANNING_RUNS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_planning_runs_project_created
ON planning_runs (project_id, created_at DESC, id DESC)
"""
_SOLUTION_PATTERN_COLUMNS = frozenset(
    {
        "solution_key",
        "recommendation_category",
        "display_name_zh",
        "short_description_zh",
        "detailed_description_zh",
        "suitable_when_zh",
        "not_suitable_when_zh",
        "typical_scope_zh",
        "human_boundary_zh",
        "expected_outputs_zh",
        "acceptance_focus_zh",
        "alternative_type",
        "review_status",
        "content_version",
        "created_at",
        "updated_at",
    }
)
_REVIEWED_CASE_COLUMNS = frozenset(
    {
        "case_id",
        "display_title_zh",
        "original_title",
        "organization",
        "case_summary_zh",
        "problem_context_zh",
        "implemented_approach_zh",
        "documented_outcomes_zh",
        "transferable_practices_zh",
        "limitations_zh",
        "applicable_solution_keys_json",
        "applicable_conditions_json",
        "non_applicable_conditions_json",
        "source_name",
        "source_url",
        "additional_sources_json",
        "evidence_grade",
        "review_status",
        "reviewed_at",
        "content_version",
        "payload_json",
    }
)
_CREATE_SOLUTION_PATTERNS_TABLE = """
CREATE TABLE IF NOT EXISTS solution_patterns (
    solution_key TEXT PRIMARY KEY NOT NULL,
    recommendation_category TEXT NOT NULL,
    display_name_zh TEXT NOT NULL,
    short_description_zh TEXT NOT NULL,
    detailed_description_zh TEXT NOT NULL,
    suitable_when_zh TEXT NOT NULL,
    not_suitable_when_zh TEXT NOT NULL,
    typical_scope_zh TEXT NOT NULL,
    human_boundary_zh TEXT NOT NULL,
    expected_outputs_zh TEXT NOT NULL,
    acceptance_focus_zh TEXT NOT NULL,
    alternative_type TEXT,
    review_status TEXT NOT NULL,
    content_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_REVIEWED_CASES_TABLE = """
CREATE TABLE IF NOT EXISTS reviewed_cases (
    case_id TEXT PRIMARY KEY NOT NULL,
    display_title_zh TEXT NOT NULL,
    original_title TEXT NOT NULL,
    organization TEXT NOT NULL,
    case_summary_zh TEXT NOT NULL,
    problem_context_zh TEXT NOT NULL,
    implemented_approach_zh TEXT NOT NULL,
    documented_outcomes_zh TEXT NOT NULL,
    transferable_practices_zh TEXT NOT NULL,
    limitations_zh TEXT NOT NULL,
    applicable_solution_keys_json TEXT NOT NULL,
    applicable_conditions_json TEXT NOT NULL,
    non_applicable_conditions_json TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    additional_sources_json TEXT NOT NULL,
    evidence_grade TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    content_version TEXT NOT NULL,
    payload_json TEXT NOT NULL
)
"""
_SOLUTION_CASE_LINK_COLUMNS = frozenset(
    {
        "solution_key",
        "case_id",
        "support_type",
        "supported_practice_keys_json",
        "applicability_note_zh",
        "limitation_note_zh",
        "review_status",
        "content_version",
    }
)
_CREATE_SOLUTION_CASE_LINKS_TABLE = """
CREATE TABLE IF NOT EXISTS solution_case_links (
    solution_key TEXT NOT NULL REFERENCES solution_patterns(solution_key),
    case_id TEXT NOT NULL REFERENCES reviewed_cases(case_id),
    support_type TEXT NOT NULL CHECK (support_type IN ('primary', 'supporting', 'contra')),
    supported_practice_keys_json TEXT NOT NULL,
    applicability_note_zh TEXT NOT NULL,
    limitation_note_zh TEXT NOT NULL,
    review_status TEXT NOT NULL,
    content_version TEXT NOT NULL,
    PRIMARY KEY (solution_key, case_id, support_type)
)
"""
_IMPLEMENTATION_REFERENCE_COLUMNS = frozenset(
    {
        "reference_key",
        "display_title_zh",
        "publisher",
        "summary_zh",
        "supported_practice_keys_json",
        "source_name",
        "source_url",
        "review_status",
        "content_version",
        "payload_json",
    }
)
_CREATE_IMPLEMENTATION_REFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS reviewed_implementation_references (
    reference_key TEXT PRIMARY KEY NOT NULL,
    display_title_zh TEXT NOT NULL,
    publisher TEXT NOT NULL,
    summary_zh TEXT NOT NULL,
    supported_practice_keys_json TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    review_status TEXT NOT NULL,
    content_version TEXT NOT NULL,
    payload_json TEXT NOT NULL
)
"""
_GOLDEN_COVERAGE_COLUMNS = frozenset(
    {
        "scenario_id",
        "expected_solution_key",
        "required_practice_keys_json",
        "minimum_primary_cases",
        "minimum_supporting_cases",
        "minimum_implementation_references",
        "content_version",
    }
)
_CREATE_GOLDEN_COVERAGE_TABLE = """
CREATE TABLE IF NOT EXISTS golden_scenario_coverage (
    scenario_id TEXT PRIMARY KEY NOT NULL,
    expected_solution_key TEXT NOT NULL REFERENCES solution_patterns(solution_key),
    required_practice_keys_json TEXT NOT NULL,
    minimum_primary_cases INTEGER NOT NULL CHECK (minimum_primary_cases >= 0),
    minimum_supporting_cases INTEGER NOT NULL CHECK (minimum_supporting_cases >= 0),
    minimum_implementation_references INTEGER NOT NULL CHECK (minimum_implementation_references >= 0),
    content_version TEXT NOT NULL
)
"""
_PLANNING_PROJECT_COLUMNS = frozenset(
    {"id", "project_name", "created_at", "updated_at"}
)
_PROJECT_VERSION_COLUMNS = frozenset(
    {
        "id",
        "project_id",
        "version_number",
        "status",
        "based_on_version_id",
        "profile_id",
        "profile_name",
        "model_name",
        "created_at",
        "updated_at",
        "completed_at",
    }
)
_MESSAGE_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "sequence",
        "role",
        "message_kind",
        "content",
        "created_at",
        "copied_from_message_id",
    }
)
_FACT_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "fact_key",
        "normalized_fact_key",
        "value_json",
        "status",
        "supersedes_fact_id",
        "copied_from_fact_id",
        "correction_reason",
        "created_at",
    }
)
_FACT_REFERENCE_COLUMNS = frozenset({"fact_id", "message_id"})
_INTERVIEW_SESSION_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "brief_message_id",
        "latest_understanding_message_id",
        "understanding_revision",
        "status",
        "current_round",
        "understanding_confirmed_at",
        "completed_at",
        "created_at",
        "updated_at",
    }
)
_INTERVIEW_QUESTION_COLUMNS = frozenset(
    {
        "id",
        "session_id",
        "version_id",
        "round_number",
        "position",
        "visible_message_id",
        "fact_key",
        "question",
        "why_it_matters",
        "affected_judgement",
        "example",
        "answer_message_id",
        "created_at",
        "answered_at",
    }
)
_ANALYSIS_RESULT_COLUMNS = frozenset(
    {
        "id",
        "version_id",
        "rubric_version",
        "hard_gate_version",
        "model_conclusion",
        "recommended_option_key",
        "weighted_total",
        "gate_disposition",
        "created_at",
        "requirement_summary",
        "conclusion_rationale",
        "overall_risks_json",
        "unresolved_gaps_json",
        "case_centered_json",
    }
)
_ANALYSIS_OPTION_COLUMNS = frozenset(
    {
        "id",
        "analysis_id",
        "option_key",
        "position",
        "option_kind",
        "title",
        "payload_json",
    }
)
_ANALYSIS_SCORE_COLUMNS = frozenset(
    {
        "id",
        "analysis_id",
        "dimension",
        "rating",
        "weight",
        "weighted_points",
        "rationale",
        "payload_json",
    }
)
_ANALYSIS_REFERENCE_COLUMNS = frozenset(
    {
        "id",
        "analysis_id",
        "token",
        "fact_revision_id",
        "fact_key",
        "fact_status",
        "reference_scope",
        "option_key",
        "dimension",
        "signal_name",
    }
)
_ANALYSIS_GATE_COLUMNS = frozenset(
    {
        "id",
        "analysis_id",
        "rule_id",
        "disposition",
        "reason",
        "payload_json",
    }
)
_REPORT_COLUMNS = frozenset(
    {"id", "version_id", "analysis_id", "report_json", "markdown", "created_at"}
)
_CREATE_PLANNING_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_projects (
    id TEXT PRIMARY KEY NOT NULL,
    project_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_PROJECT_VERSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_project_versions (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES planning_projects(id),
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    status TEXT NOT NULL,
    based_on_version_id TEXT REFERENCES planning_project_versions(id),
    profile_id TEXT,
    profile_name TEXT,
    model_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE (project_id, version_number),
    CHECK (
        (profile_id IS NULL AND profile_name IS NULL AND model_name IS NULL)
        OR (
            profile_id IS NOT NULL
            AND profile_name IS NOT NULL
            AND model_name IS NOT NULL
        )
    )
)
"""
_CREATE_VISIBLE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS visible_conversation_messages (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES planning_project_versions(id),
    sequence INTEGER NOT NULL CHECK (sequence >= 1),
    role TEXT NOT NULL,
    message_kind TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    copied_from_message_id TEXT REFERENCES visible_conversation_messages(id),
    UNIQUE (version_id, sequence)
)
"""
_CREATE_FACT_REVISIONS_TABLE = """
CREATE TABLE IF NOT EXISTS project_fact_revisions (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES planning_project_versions(id),
    fact_key TEXT NOT NULL,
    normalized_fact_key TEXT NOT NULL,
    value_json TEXT,
    status TEXT NOT NULL,
    supersedes_fact_id TEXT REFERENCES project_fact_revisions(id),
    copied_from_fact_id TEXT REFERENCES project_fact_revisions(id),
    correction_reason TEXT,
    created_at TEXT NOT NULL
)
"""
_CREATE_FACT_REFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS fact_message_references (
    fact_id TEXT NOT NULL REFERENCES project_fact_revisions(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL REFERENCES visible_conversation_messages(id),
    PRIMARY KEY (fact_id, message_id)
)
"""
_CREATE_INTERVIEW_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_interview_sessions (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL UNIQUE REFERENCES planning_project_versions(id),
    brief_message_id TEXT NOT NULL REFERENCES visible_conversation_messages(id),
    latest_understanding_message_id TEXT REFERENCES visible_conversation_messages(id),
    understanding_revision INTEGER NOT NULL CHECK (understanding_revision >= 0),
    status TEXT NOT NULL,
    current_round INTEGER NOT NULL CHECK (current_round BETWEEN 0 AND 3),
    understanding_confirmed_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_CREATE_INTERVIEW_QUESTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_interview_questions (
    id TEXT PRIMARY KEY NOT NULL,
    session_id TEXT NOT NULL REFERENCES planning_interview_sessions(id),
    version_id TEXT NOT NULL REFERENCES planning_project_versions(id),
    round_number INTEGER NOT NULL CHECK (round_number BETWEEN 1 AND 3),
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 3),
    visible_message_id TEXT NOT NULL REFERENCES visible_conversation_messages(id),
    fact_key TEXT NOT NULL,
    question TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    affected_judgement TEXT NOT NULL,
    example TEXT NOT NULL,
    answer_message_id TEXT REFERENCES visible_conversation_messages(id),
    created_at TEXT NOT NULL,
    answered_at TEXT,
    UNIQUE (session_id, round_number, position)
)
"""
_CREATE_INTERVIEW_SESSION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_interview_sessions_version
ON planning_interview_sessions(version_id)
"""
_CREATE_INTERVIEW_QUESTION_ORDER_INDEX = """
CREATE INDEX IF NOT EXISTS idx_interview_questions_order
ON planning_interview_questions(session_id, round_number, position)
"""
_CREATE_ANALYSIS_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_analysis_results (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL UNIQUE REFERENCES planning_project_versions(id),
    rubric_version TEXT NOT NULL,
    hard_gate_version TEXT NOT NULL,
    model_conclusion TEXT NOT NULL,
    recommended_option_key TEXT NOT NULL,
    weighted_total INTEGER NOT NULL CHECK (weighted_total BETWEEN 0 AND 100),
    gate_disposition TEXT NOT NULL,
    created_at TEXT NOT NULL,
    requirement_summary TEXT NOT NULL,
    conclusion_rationale TEXT NOT NULL,
    overall_risks_json TEXT NOT NULL,
    unresolved_gaps_json TEXT NOT NULL,
    case_centered_json TEXT
)
"""
_CREATE_ANALYSIS_OPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_analysis_options (
    id TEXT PRIMARY KEY NOT NULL,
    analysis_id TEXT NOT NULL REFERENCES planning_analysis_results(id),
    option_key TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 1),
    option_kind TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (analysis_id, option_key),
    UNIQUE (analysis_id, position)
)
"""
_CREATE_ANALYSIS_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS planning_analysis_scores (
    id TEXT PRIMARY KEY NOT NULL,
    analysis_id TEXT NOT NULL REFERENCES planning_analysis_results(id),
    dimension TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    weight INTEGER NOT NULL,
    weighted_points INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (analysis_id, dimension)
)
"""
_CREATE_ANALYSIS_REFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS planning_analysis_fact_references (
    id TEXT PRIMARY KEY NOT NULL,
    analysis_id TEXT NOT NULL REFERENCES planning_analysis_results(id),
    token TEXT NOT NULL,
    fact_revision_id TEXT NOT NULL REFERENCES project_fact_revisions(id),
    fact_key TEXT NOT NULL,
    fact_status TEXT NOT NULL,
    reference_scope TEXT NOT NULL,
    option_key TEXT,
    dimension TEXT,
    signal_name TEXT
)
"""
_CREATE_ANALYSIS_GATES_TABLE = """
CREATE TABLE IF NOT EXISTS planning_analysis_gate_results (
    id TEXT PRIMARY KEY NOT NULL,
    analysis_id TEXT NOT NULL REFERENCES planning_analysis_results(id),
    rule_id TEXT NOT NULL,
    disposition TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (analysis_id, rule_id)
)
"""
_CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS planning_reports (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL UNIQUE REFERENCES planning_project_versions(id),
    analysis_id TEXT NOT NULL UNIQUE REFERENCES planning_analysis_results(id),
    report_json TEXT NOT NULL,
    markdown TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""
_CREATE_REPORT_VERSION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_planning_reports_version ON planning_reports(version_id)
"""
_CREATE_REPORT_IMMUTABILITY_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_report_update
BEFORE UPDATE ON planning_reports BEGIN SELECT RAISE(ABORT, 'report is immutable'); END
"""
_CREATE_REPORT_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_report_delete
BEFORE DELETE ON planning_reports BEGIN SELECT RAISE(ABORT, 'report is immutable'); END
"""
_CREATE_ANALYSIS_VERSION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_analysis_results_version
ON planning_analysis_results (version_id)
"""
_CREATE_ANALYSIS_REFERENCE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_analysis_fact_references_fact
ON planning_analysis_fact_references (fact_revision_id, analysis_id)
"""
_CREATE_ANALYSIS_IMMUTABILITY_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_analysis_result_update
BEFORE UPDATE ON planning_analysis_results
BEGIN
    SELECT RAISE(ABORT, 'analysis result is immutable');
END
"""
_CREATE_ANALYSIS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_analysis_result_delete
BEFORE DELETE ON planning_analysis_results
BEGIN
    SELECT RAISE(ABORT, 'analysis result is immutable');
END
"""
_CREATE_COMPLETED_SESSION_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_session_write
BEFORE INSERT ON planning_interview_sessions
WHEN (SELECT status FROM planning_project_versions
      WHERE id = NEW.version_id) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_SESSION_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_session_update
BEFORE UPDATE ON planning_interview_sessions
WHEN (SELECT status FROM planning_project_versions
      WHERE id = OLD.version_id) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_QUESTION_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_question_write
BEFORE INSERT ON planning_interview_questions
WHEN (SELECT status FROM planning_project_versions
      WHERE id = NEW.version_id) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_QUESTION_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_question_update
BEFORE UPDATE ON planning_interview_questions
WHEN (SELECT status FROM planning_project_versions
      WHERE id = OLD.version_id) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_PROJECT_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_planning_projects_updated
ON planning_projects (updated_at DESC, id DESC)
"""
_CREATE_VERSION_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_project_versions_history
ON planning_project_versions (project_id, version_number DESC)
"""
_CREATE_MESSAGE_ORDER_INDEX = """
CREATE INDEX IF NOT EXISTS idx_visible_messages_order
ON visible_conversation_messages (version_id, sequence)
"""
_CREATE_FACT_CURRENT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_fact_revisions_current
ON project_fact_revisions (version_id, normalized_fact_key, supersedes_fact_id)
"""
_CREATE_FACT_REFERENCE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_fact_references_message
ON fact_message_references (message_id, fact_id)
"""
_CREATE_COMPLETED_VERSION_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_update
BEFORE UPDATE ON planning_project_versions
WHEN OLD.status = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_VERSION_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_delete
BEFORE DELETE ON planning_project_versions
WHEN OLD.status = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_write
BEFORE INSERT ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = NEW.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_update
BEFORE UPDATE ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_MESSAGE_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_message_delete
BEFORE DELETE ON visible_conversation_messages
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_write
BEFORE INSERT ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = NEW.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_update
BEFORE UPDATE ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_delete
BEFORE DELETE ON project_fact_revisions
WHEN (
    SELECT status FROM planning_project_versions WHERE id = OLD.version_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_write
BEFORE INSERT ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = NEW.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_update
BEFORE UPDATE ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = OLD.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""
_CREATE_COMPLETED_FACT_REFERENCE_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS prevent_completed_version_fact_reference_delete
BEFORE DELETE ON fact_message_references
WHEN (
    SELECT v.status
    FROM project_fact_revisions f
    JOIN planning_project_versions v ON v.id = f.version_id
    WHERE f.id = OLD.fact_id
) = 'complete'
BEGIN
    SELECT RAISE(ABORT, 'completed version is immutable');
END
"""


def read_schema_version(connection: sqlite3.Connection) -> int:
    """Return SQLite's application-controlled schema version."""
    try:
        row = connection.execute("PRAGMA user_version").fetchone()
    except sqlite3.Error as error:
        raise DatabaseOperationError(
            "unable to read database schema version"
        ) from error
    if row is None:
        raise SchemaMismatchError("database schema version is unavailable")
    return int(row[0])


def _validate_project_table(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(analysis_projects)")
    }
    if not _PROJECT_COLUMNS <= columns:
        raise SchemaMismatchError(
            "analysis project table is missing required schema fields"
        )


def _validate_planning_run_table(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(planning_runs)")}
    if not _PLANNING_RUN_COLUMNS <= columns:
        raise SchemaMismatchError(
            "planning run table is missing required schema fields"
        )
    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(planning_runs)"
    ).fetchall()
    project_key_exists = any(
        row[2] == "analysis_projects" and row[3] == "project_id" and row[4] == "id"
        for row in foreign_keys
    )
    if not project_key_exists:
        raise SchemaMismatchError(
            "planning run table is missing the analysis project foreign key"
        )


def _validate_current_schema(connection: sqlite3.Connection) -> None:
    _validate_project_table(connection)
    _validate_planning_run_table(connection)
    _validate_phase_two_tables(connection)
    _validate_phase_three_tables(connection)
    _validate_phase_four_tables(connection)
    _validate_phase_five_tables(connection)
    _validate_catalog_tables(connection)


def _ensure_case_centered_column(connection: sqlite3.Connection) -> None:
    """Add the additive result payload to an existing v6 database."""

    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(planning_analysis_results)")
    }
    if columns and "case_centered_json" not in columns:
        connection.execute(
            "ALTER TABLE planning_analysis_results ADD COLUMN case_centered_json TEXT"
        )


def _validate_columns(
    connection: sqlite3.Connection,
    table: str,
    required_columns: frozenset[str],
) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if not required_columns <= columns:
        raise SchemaMismatchError(f"{table} is missing required schema fields")


def _validate_phase_two_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(connection, "planning_projects", _PLANNING_PROJECT_COLUMNS)
    _validate_columns(
        connection,
        "planning_project_versions",
        _PROJECT_VERSION_COLUMNS,
    )
    _validate_columns(connection, "visible_conversation_messages", _MESSAGE_COLUMNS)
    _validate_columns(connection, "project_fact_revisions", _FACT_COLUMNS)
    _validate_columns(connection, "fact_message_references", _FACT_REFERENCE_COLUMNS)


def _validate_phase_three_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(
        connection, "planning_interview_sessions", _INTERVIEW_SESSION_COLUMNS
    )
    _validate_columns(
        connection, "planning_interview_questions", _INTERVIEW_QUESTION_COLUMNS
    )


def _validate_phase_four_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(connection, "planning_analysis_results", _ANALYSIS_RESULT_COLUMNS)
    _validate_columns(connection, "planning_analysis_options", _ANALYSIS_OPTION_COLUMNS)
    _validate_columns(connection, "planning_analysis_scores", _ANALYSIS_SCORE_COLUMNS)
    _validate_columns(
        connection, "planning_analysis_fact_references", _ANALYSIS_REFERENCE_COLUMNS
    )
    _validate_columns(
        connection, "planning_analysis_gate_results", _ANALYSIS_GATE_COLUMNS
    )


def _validate_phase_five_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(connection, "planning_reports", _REPORT_COLUMNS)


def _validate_catalog_tables(connection: sqlite3.Connection) -> None:
    _validate_columns(connection, "solution_patterns", _SOLUTION_PATTERN_COLUMNS)
    _validate_columns(connection, "reviewed_cases", _REVIEWED_CASE_COLUMNS)
    _validate_columns(connection, "solution_case_links", _SOLUTION_CASE_LINK_COLUMNS)
    _validate_columns(
        connection,
        "reviewed_implementation_references",
        _IMPLEMENTATION_REFERENCE_COLUMNS,
    )
    _validate_columns(connection, "golden_scenario_coverage", _GOLDEN_COVERAGE_COLUMNS)


def _create_phase_two_schema(connection: sqlite3.Connection) -> None:
    for statement in (
        _CREATE_PLANNING_PROJECTS_TABLE,
        _CREATE_PROJECT_VERSIONS_TABLE,
        _CREATE_VISIBLE_MESSAGES_TABLE,
        _CREATE_FACT_REVISIONS_TABLE,
        _CREATE_FACT_REFERENCES_TABLE,
        _CREATE_PROJECT_HISTORY_INDEX,
        _CREATE_VERSION_HISTORY_INDEX,
        _CREATE_MESSAGE_ORDER_INDEX,
        _CREATE_FACT_CURRENT_INDEX,
        _CREATE_FACT_REFERENCE_INDEX,
        _CREATE_COMPLETED_VERSION_TRIGGER,
        _CREATE_COMPLETED_VERSION_DELETE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_UPDATE_TRIGGER,
        _CREATE_COMPLETED_MESSAGE_DELETE_TRIGGER,
        _CREATE_COMPLETED_FACT_TRIGGER,
        _CREATE_COMPLETED_FACT_UPDATE_TRIGGER,
        _CREATE_COMPLETED_FACT_DELETE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_UPDATE_TRIGGER,
        _CREATE_COMPLETED_FACT_REFERENCE_DELETE_TRIGGER,
    ):
        connection.execute(statement)


def _create_phase_three_schema(connection: sqlite3.Connection) -> None:
    for statement in (
        _CREATE_INTERVIEW_SESSIONS_TABLE,
        _CREATE_INTERVIEW_QUESTIONS_TABLE,
        _CREATE_INTERVIEW_SESSION_INDEX,
        _CREATE_INTERVIEW_QUESTION_ORDER_INDEX,
        _CREATE_COMPLETED_SESSION_TRIGGER,
        _CREATE_COMPLETED_SESSION_UPDATE_TRIGGER,
        _CREATE_COMPLETED_QUESTION_TRIGGER,
        _CREATE_COMPLETED_QUESTION_UPDATE_TRIGGER,
    ):
        connection.execute(statement)


def _create_phase_four_schema(connection: sqlite3.Connection) -> None:
    for statement in (
        _CREATE_ANALYSIS_RESULTS_TABLE,
        _CREATE_ANALYSIS_OPTIONS_TABLE,
        _CREATE_ANALYSIS_SCORES_TABLE,
        _CREATE_ANALYSIS_REFERENCES_TABLE,
        _CREATE_ANALYSIS_GATES_TABLE,
        _CREATE_ANALYSIS_VERSION_INDEX,
        _CREATE_ANALYSIS_REFERENCE_INDEX,
        _CREATE_ANALYSIS_IMMUTABILITY_TRIGGER,
        _CREATE_ANALYSIS_DELETE_TRIGGER,
    ):
        connection.execute(statement)


def _create_phase_five_schema(connection: sqlite3.Connection) -> None:
    for statement in (
        _CREATE_REPORTS_TABLE,
        _CREATE_REPORT_VERSION_INDEX,
        _CREATE_REPORT_IMMUTABILITY_TRIGGER,
        _CREATE_REPORT_DELETE_TRIGGER,
    ):
        connection.execute(statement)


def _create_catalog_schema(connection: sqlite3.Connection) -> None:
    connection.execute(_CREATE_SOLUTION_PATTERNS_TABLE)
    connection.execute(_CREATE_REVIEWED_CASES_TABLE)
    connection.execute(_CREATE_SOLUTION_CASE_LINKS_TABLE)
    connection.execute(_CREATE_IMPLEMENTATION_REFERENCES_TABLE)
    connection.execute(_CREATE_GOLDEN_COVERAGE_TABLE)


def _rebuild_solution_patterns_without_category_unique(
    connection: sqlite3.Connection,
) -> None:
    """Upgrade v7's one-row-per-category table for many candidate routes."""

    indexes = connection.execute("PRAGMA index_list(solution_patterns)").fetchall()
    has_category_unique = False
    for index in indexes:
        if not index[2]:
            continue
        columns = connection.execute(f"PRAGMA index_info({index[1]})").fetchall()
        if [row[2] for row in columns] == ["recommendation_category"]:
            has_category_unique = True
            break
    if not has_category_unique:
        return
    connection.execute("ALTER TABLE solution_patterns RENAME TO solution_patterns_v7")
    connection.execute(_CREATE_SOLUTION_PATTERNS_TABLE)
    old_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(solution_patterns_v7)")
    }
    alternative_expression = (
        "alternative_type" if "alternative_type" in old_columns else "NULL"
    )
    connection.execute(
        f"""
        INSERT INTO solution_patterns (
            solution_key, recommendation_category, display_name_zh,
            short_description_zh, detailed_description_zh, suitable_when_zh,
            not_suitable_when_zh, typical_scope_zh, human_boundary_zh,
            expected_outputs_zh, acceptance_focus_zh, alternative_type,
            review_status, content_version, created_at, updated_at
        )
        SELECT solution_key, recommendation_category, display_name_zh,
            short_description_zh, detailed_description_zh, suitable_when_zh,
            not_suitable_when_zh, typical_scope_zh, human_boundary_zh,
            expected_outputs_zh, acceptance_focus_zh, {alternative_expression},
            review_status, content_version, created_at, updated_at
        FROM solution_patterns_v7
        """
    )
    connection.execute("DROP TABLE solution_patterns_v7")


def _seed_reviewed_catalogue(connection: sqlite3.Connection) -> None:
    """Upsert versioned editorial content without letting a provider write it."""

    from ai_poc_planner.persistence.catalog_seed import (
        golden_scenario_coverage,
        implementation_references,
        reviewed_cases,
        reviewed_solution_patterns,
        solution_case_links,
    )

    for solution in reviewed_solution_patterns():
        values = solution.model_dump(mode="json")
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column != "solution_key"
        )
        connection.execute(
            f"""
            INSERT INTO solution_patterns ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(solution_key) DO UPDATE SET {updates}
            WHERE excluded.content_version > solution_patterns.content_version
            """,
            tuple(values[column] for column in columns),
        )
    for case in reviewed_cases():
        payload = case.model_dump(mode="json")
        values = {
            "case_id": case.case_id,
            "display_title_zh": case.display_title_zh,
            "original_title": case.original_title,
            "organization": case.organization,
            "case_summary_zh": case.case_summary_zh,
            "problem_context_zh": case.problem_context_zh,
            "implemented_approach_zh": case.implemented_approach_zh,
            "documented_outcomes_zh": case.documented_outcomes_zh,
            "transferable_practices_zh": case.transferable_practices_zh,
            "limitations_zh": case.limitations_zh,
            "applicable_solution_keys_json": json.dumps(case.applicable_solution_keys),
            "applicable_conditions_json": json.dumps(case.applicable_conditions),
            "non_applicable_conditions_json": json.dumps(
                case.non_applicable_conditions
            ),
            "source_name": case.source_name,
            "source_url": str(case.source_url),
            "additional_sources_json": json.dumps(
                [item.model_dump(mode="json") for item in case.additional_sources]
            ),
            "evidence_grade": case.evidence_grade.value,
            "review_status": case.review_status.value,
            "reviewed_at": case.reviewed_at,
            "content_version": case.content_version,
            "payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        }
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}" for column in columns if column != "case_id"
        )
        connection.execute(
            f"""
            INSERT INTO reviewed_cases ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(case_id) DO UPDATE SET {updates}
            WHERE excluded.content_version > reviewed_cases.content_version
            """,
            tuple(values[column] for column in columns),
        )
    for link in solution_case_links():
        values = link.model_dump(mode="json")
        values["supported_practice_keys_json"] = json.dumps(
            values.pop("supported_practice_keys"), ensure_ascii=False
        )
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column not in {"solution_key", "case_id", "support_type"}
        )
        connection.execute(
            f"""
            INSERT INTO solution_case_links ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(solution_key, case_id, support_type) DO UPDATE SET {updates}
            WHERE excluded.content_version > solution_case_links.content_version
            """,
            tuple(values[column] for column in columns),
        )
    for reference in implementation_references():
        payload = reference.model_dump(mode="json")
        supported_practice_keys = payload.pop("supported_practice_keys")
        values = {
            **payload,
            "supported_practice_keys_json": json.dumps(
                supported_practice_keys, ensure_ascii=False
            ),
            "source_url": str(reference.source_url),
            "payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        }
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column != "reference_key"
        )
        connection.execute(
            f"""
            INSERT INTO reviewed_implementation_references ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(reference_key) DO UPDATE SET {updates}
            WHERE excluded.content_version > reviewed_implementation_references.content_version
            """,
            tuple(values[column] for column in columns),
        )
    for coverage in golden_scenario_coverage():
        values = coverage.model_dump(mode="json")
        values["required_practice_keys_json"] = json.dumps(
            values.pop("required_practice_keys"), ensure_ascii=False
        )
        columns = tuple(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(
            f"{column} = excluded.{column}"
            for column in columns
            if column != "scenario_id"
        )
        connection.execute(
            f"""
            INSERT INTO golden_scenario_coverage ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(scenario_id) DO UPDATE SET {updates}
            WHERE excluded.content_version > golden_scenario_coverage.content_version
            """,
            tuple(values[column] for column in columns),
        )


def _phase_two_table_count(connection: sqlite3.Connection) -> int:
    names = {
        "planning_projects",
        "planning_project_versions",
        "visible_conversation_messages",
        "project_fact_revisions",
        "fact_message_references",
    }
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return sum(row[0] in names for row in rows)


def _rollback_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create schema v8 or additively upgrade supported legacy databases."""
    version = read_schema_version(connection)
    if version not in {0, 1, 2, 3, 4, 5, 6, 7, CURRENT_SCHEMA_VERSION}:
        raise UnsupportedSchemaVersionError(
            "database schema version is not supported by this application"
        )

    if version == CURRENT_SCHEMA_VERSION:
        try:
            _ensure_case_centered_column(connection)
            _create_catalog_schema(connection)
            _rebuild_solution_patterns_without_category_unique(connection)
            _seed_reviewed_catalogue(connection)
            _validate_current_schema(connection)
            connection.commit()
        except SchemaMismatchError:
            raise
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to validate database schema"
            ) from error
        return

    try:
        connection.execute("BEGIN")
        if version == 0:
            connection.execute(_CREATE_PROJECTS_TABLE)
        _validate_project_table(connection)
        connection.execute(_CREATE_PLANNING_RUNS_TABLE)
        connection.execute(_CREATE_PLANNING_RUNS_INDEX)
        _validate_planning_run_table(connection)
        if _phase_two_table_count(connection):
            _validate_phase_two_tables(connection)
        _create_phase_two_schema(connection)
        _validate_phase_two_tables(connection)
        _create_phase_three_schema(connection)
        _validate_phase_three_tables(connection)
        _create_phase_four_schema(connection)
        _validate_phase_four_tables(connection)
        _create_phase_five_schema(connection)
        _validate_phase_five_tables(connection)
        _create_catalog_schema(connection)
        _rebuild_solution_patterns_without_category_unique(connection)
        _seed_reviewed_catalogue(connection)
        _validate_catalog_tables(connection)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
        connection.commit()
    except SchemaMismatchError:
        _rollback_quietly(connection)
        raise
    except sqlite3.Error as error:
        _rollback_quietly(connection)
        raise DatabaseOperationError("unable to initialize database schema") from error
