"""Presentation-only helpers for the Phase 3 discovery HTTP flow."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_DISCOVERY_VIEWS = {
    "brief_submitted": "understanding_generation",
    "correction_pending": "understanding_generation",
    "awaiting_understanding_confirmation": "understanding_confirmation",
    "ready_for_interview": "next_round",
    "ready_for_next_round": "next_round",
    "awaiting_answers": "interview_answers",
    "ready_for_assessment": "complete",
}


def discovery_view_for_status(status: object) -> str:
    """Map only the API's durable session status to a presentation step."""

    return _DISCOVERY_VIEWS.get(str(status), "unavailable")


def question_details(question: Mapping[str, Any]) -> dict[str, str]:
    """Keep identifiers and provider metadata out of question presentation."""

    return {
        field: str(question[field])
        for field in (
            "question",
            "why_it_matters",
            "affected_judgement",
            "example",
        )
    }


def interview_payload(
    *,
    answers: Sequence[Mapping[str, Any]],
    additional_fact: Mapping[str, Any] | None = None,
    correction: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Shape user-entered choices for the existing round-answer contract."""

    return {
        "answers": [dict(answer) for answer in answers],
        "additional_facts": [dict(additional_fact)] if additional_fact else [],
        "corrections": [dict(correction)] if correction else [],
    }


def facts_summary(
    facts: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Present only readable confirmed and unresolved fact summaries."""

    confirmed = [
        {"fact_key": str(fact["fact_key"]), "value": fact.get("value")}
        for fact in facts
        if fact.get("status") == "confirmed"
    ]
    unknown_or_missing = [
        {"fact_key": str(fact["fact_key"]), "status": str(fact["status"])}
        for fact in facts
        if fact.get("status") in {"unknown", "missing"}
    ]
    return {"confirmed": confirmed, "unknown_or_missing": unknown_or_missing}
