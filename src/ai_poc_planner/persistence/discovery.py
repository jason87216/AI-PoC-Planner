"""SQLite storage for durable Phase 3 session and question records."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from uuid import UUID

from pydantic import ValidationError

from ai_poc_planner.domain.discovery import DiscoverySession, InterviewQuestion
from ai_poc_planner.persistence.errors import (
    DatabaseOperationError,
    InterviewSessionNotFoundError,
)


class SQLiteDiscoveryRepository:
    """Persists only visible interview state; its caller owns transactions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create_session(self, session: DiscoverySession) -> DiscoverySession:
        try:
            self._connection.execute(
                "INSERT INTO planning_interview_sessions "
                "(id, version_id, brief_message_id, latest_understanding_message_id, "
                "understanding_revision, status, current_round, "
                "understanding_confirmed_at, completed_at, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(session.id),
                    str(session.version_id),
                    str(session.brief_message_id),
                    str(session.latest_understanding_message_id)
                    if session.latest_understanding_message_id
                    else None,
                    session.understanding_revision,
                    session.status.value,
                    session.current_round,
                    session.understanding_confirmed_at.isoformat()
                    if session.understanding_confirmed_at
                    else None,
                    session.completed_at.isoformat() if session.completed_at else None,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                ),
            )
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to create discovery session"
            ) from error
        return session

    def get_session_for_version(self, version_id: UUID) -> DiscoverySession:
        try:
            row = self._connection.execute(
                "SELECT * FROM planning_interview_sessions WHERE version_id = ?",
                (str(version_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load discovery session") from error
        if row is None:
            raise InterviewSessionNotFoundError("discovery session was not found")
        return self._session_from_row(row)

    def update_session(self, session: DiscoverySession) -> DiscoverySession:
        try:
            cursor = self._connection.execute(
                "UPDATE planning_interview_sessions SET "
                "latest_understanding_message_id=?, understanding_revision=?, "
                "status=?, current_round=?, understanding_confirmed_at=?, "
                "completed_at=?, updated_at=? "
                "WHERE id=?",
                (
                    str(session.latest_understanding_message_id)
                    if session.latest_understanding_message_id
                    else None,
                    session.understanding_revision,
                    session.status.value,
                    session.current_round,
                    session.understanding_confirmed_at.isoformat()
                    if session.understanding_confirmed_at
                    else None,
                    session.completed_at.isoformat() if session.completed_at else None,
                    session.updated_at.isoformat(),
                    str(session.id),
                ),
            )
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to update discovery session"
            ) from error
        if cursor.rowcount != 1:
            raise InterviewSessionNotFoundError("discovery session was not found")
        return session

    def create_question(self, question: InterviewQuestion) -> InterviewQuestion:
        try:
            self._connection.execute(
                "INSERT INTO planning_interview_questions "
                "(id, session_id, version_id, round_number, position, "
                "visible_message_id, fact_key, question, why_it_matters, "
                "affected_judgement, example, answer_message_id, created_at, "
                "answered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(question.id),
                    str(question.session_id),
                    str(question.version_id),
                    question.round_number,
                    question.position,
                    str(question.visible_message_id),
                    question.fact_key,
                    question.question,
                    question.why_it_matters,
                    question.affected_judgement,
                    question.example,
                    str(question.answer_message_id)
                    if question.answer_message_id
                    else None,
                    question.created_at.isoformat(),
                    question.answered_at.isoformat() if question.answered_at else None,
                ),
            )
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to create interview question"
            ) from error
        return question

    def list_questions(self, session_id: UUID) -> list[InterviewQuestion]:
        try:
            rows = self._connection.execute(
                "SELECT * FROM planning_interview_questions WHERE session_id=? "
                "ORDER BY round_number, position",
                (str(session_id),),
            ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseOperationError(
                "unable to list interview questions"
            ) from error
        return [self._question_from_row(row) for row in rows]

    def get_question(self, question_id: UUID) -> InterviewQuestion:
        try:
            row = self._connection.execute(
                "SELECT * FROM planning_interview_questions WHERE id=?",
                (str(question_id),),
            ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to load interview question") from error
        if row is None:
            raise InterviewSessionNotFoundError("interview question was not found")
        return self._question_from_row(row)

    def answer_question(
        self, question_id: UUID, answer_message_id: UUID, answered_at: datetime
    ) -> None:
        try:
            cursor = self._connection.execute(
                "UPDATE planning_interview_questions SET answer_message_id=?, "
                "answered_at=? "
                "WHERE id=? AND answer_message_id IS NULL",
                (str(answer_message_id), answered_at.isoformat(), str(question_id)),
            )
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to record interview answer") from error
        if cursor.rowcount != 1:
            raise DatabaseOperationError("interview question was already answered")

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> DiscoverySession:
        try:
            return DiscoverySession.model_validate(dict(row))
        except ValidationError as error:
            raise DatabaseOperationError(
                "stored discovery session is invalid"
            ) from error

    @staticmethod
    def _question_from_row(row: sqlite3.Row) -> InterviewQuestion:
        try:
            return InterviewQuestion.model_validate(dict(row))
        except ValidationError as error:
            raise DatabaseOperationError(
                "stored interview question is invalid"
            ) from error
