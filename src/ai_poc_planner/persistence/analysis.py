"""Immutable SQLite storage for validated Phase 4 analysis results."""

# ruff: noqa: E501

from __future__ import annotations

import json
import sqlite3
from uuid import UUID

from pydantic import ValidationError

from ai_poc_planner.domain.analysis import ValidatedAnalysisResult
from ai_poc_planner.persistence.errors import DatabaseOperationError


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SQLiteAnalysisRepository:
    """Stores normalized analysis records, never opaque provider payloads."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_by_version(self, version_id: UUID) -> ValidatedAnalysisResult | None:
        row = self._connection.execute(
            "SELECT * FROM planning_analysis_results WHERE version_id = ?",
            (str(version_id),),
        ).fetchone()
        if row is None:
            return None
        try:
            options = [
                json.loads(item[0])
                for item in self._connection.execute(
                    "SELECT payload_json FROM planning_analysis_options "
                    "WHERE analysis_id = ? ORDER BY position",
                    (row["id"],),
                ).fetchall()
            ]
            scores = [
                {
                    **json.loads(item[0]),
                    "weight": item[1],
                    "weighted_points": item[2],
                }
                for item in self._connection.execute(
                    "SELECT payload_json, weight, weighted_points "
                    "FROM planning_analysis_scores WHERE analysis_id = ? "
                    "ORDER BY dimension",
                    (row["id"],),
                ).fetchall()
            ]
            gates = [
                json.loads(item[0])
                for item in self._connection.execute(
                    "SELECT payload_json FROM planning_analysis_gate_results "
                    "WHERE analysis_id = ? ORDER BY rule_id",
                    (row["id"],),
                ).fetchall()
            ]
            references = [
                item[0]
                for item in self._connection.execute(
                    "SELECT token FROM planning_analysis_fact_references "
                    "WHERE analysis_id = ? ORDER BY token",
                    (row["id"],),
                ).fetchall()
            ]
            return ValidatedAnalysisResult.model_validate(
                {
                    "id": row["id"],
                    "version_id": row["version_id"],
                    "rubric_version": row["rubric_version"],
                    "hard_gate_version": row["hard_gate_version"],
                    "requirement_summary": row["requirement_summary"],
                    "options": options,
                    "recommended_option_key": row["recommended_option_key"],
                    "conclusion": row["model_conclusion"],
                    "conclusion_rationale": row["conclusion_rationale"],
                    "conclusion_fact_refs": references,
                    "scores": scores,
                    "weighted_total": row["weighted_total"],
                    "gate_results": gates,
                    "gate_disposition": row["gate_disposition"],
                    "overall_risks": json.loads(row["overall_risks_json"]),
                    "unresolved_gaps": json.loads(row["unresolved_gaps_json"]),
                    "created_at": row["created_at"],
                }
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValidationError) as error:
            raise DatabaseOperationError("stored analysis is invalid") from error

    def create(
        self, result: ValidatedAnalysisResult, references: dict[str, UUID]
    ) -> None:
        try:
            self._connection.execute(
                "INSERT INTO planning_analysis_results "
                "(id, version_id, rubric_version, hard_gate_version, model_conclusion, "
                "recommended_option_key, weighted_total, gate_disposition, created_at, "
                "requirement_summary, conclusion_rationale, overall_risks_json, unresolved_gaps_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(result.id),
                    str(result.version_id),
                    result.rubric_version,
                    result.hard_gate_version,
                    result.conclusion.value,
                    result.recommended_option_key,
                    result.weighted_total,
                    result.gate_disposition.value,
                    result.created_at.isoformat(),
                    result.requirement_summary,
                    result.conclusion_rationale,
                    _json(result.overall_risks),
                    _json(result.unresolved_gaps),
                ),
            )
            for position, option in enumerate(result.options, start=1):
                self._connection.execute(
                    "INSERT INTO planning_analysis_options "
                    "(id, analysis_id, option_key, position, option_kind, title, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{result.id}:option:{position}",
                        str(result.id),
                        option.option_key,
                        position,
                        option.option_kind.value,
                        option.title,
                        _json(option.model_dump(mode="json")),
                    ),
                )
            for score in result.scores:
                payload = score.model_dump(
                    mode="json", exclude={"weight", "weighted_points"}
                )
                self._connection.execute(
                    "INSERT INTO planning_analysis_scores "
                    "(id, analysis_id, dimension, rating, weight, weighted_points, rationale, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        f"{result.id}:score:{score.dimension.value}",
                        str(result.id),
                        score.dimension.value,
                        score.rating,
                        score.weight,
                        score.weighted_points,
                        score.rationale,
                        _json(payload),
                    ),
                )
            for gate in result.gate_results:
                self._connection.execute(
                    "INSERT INTO planning_analysis_gate_results "
                    "(id, analysis_id, rule_id, disposition, reason, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        f"{result.id}:gate:{gate.rule_id}",
                        str(result.id),
                        gate.rule_id,
                        gate.disposition.value,
                        gate.reason,
                        _json(gate.model_dump(mode="json")),
                    ),
                )
            for token, revision_id in references.items():
                self._connection.execute(
                    "INSERT INTO planning_analysis_fact_references "
                    "(id, analysis_id, token, fact_revision_id, fact_key, fact_status, reference_scope) "
                    "SELECT ?, ?, ?, id, fact_key, status, ? FROM project_fact_revisions WHERE id = ?",
                    (
                        f"{result.id}:ref:{token}",
                        str(result.id),
                        token,
                        "catalog",
                        str(revision_id),
                    ),
                )
        except sqlite3.Error as error:
            raise DatabaseOperationError("unable to persist analysis") from error
