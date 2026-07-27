"""Presentation-only helpers for the product discovery HTTP flow."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
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

_FACT_LABELS = {
    "current_workflow_problem": "目前流程與問題",
    "desired_outcome": "希望改善的成果",
    "available_data": "現有資料與文件",
    "users_and_owners": "使用者與負責人",
    "known_constraints": "已知限制",
}


def select_active_project(
    state: MutableMapping[str, Any], project_id: str, version_number: int
) -> None:
    state["selected_project"] = {
        "project_id": project_id,
        "version_number": version_number,
    }


def discovery_view_for_status(status: object) -> str:
    return _DISCOVERY_VIEWS.get(str(status), "unavailable")


def question_details(question: Mapping[str, Any]) -> dict[str, str]:
    return {
        field: str(question[field])
        for field in ("question", "why_it_matters", "affected_judgement", "example")
    }


def interview_payload(
    *, answers: Sequence[Mapping[str, Any]], supplementary_note: str | None = None
) -> dict[str, Any]:
    return {
        "answers": [dict(answer) for answer in answers],
        "additional_facts": [],
        "corrections": [],
        "supplementary_note": supplementary_note or None,
    }


def facts_summary(facts: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    confirmed: list[str] = []
    unresolved: list[str] = []
    for fact in facts:
        key, status = str(fact.get("fact_key", "")), str(fact.get("status", ""))
        if key.startswith(("clarification_", "supplementary_", "user_")):
            continue
        label = _FACT_LABELS.get(key)
        if label is None:
            continue
        if status == "confirmed" and fact.get("value"):
            confirmed.append(f"{label}：{fact['value']}")
        elif status in {"unknown", "missing"}:
            unresolved.append(label)
    return {"confirmed": confirmed, "unresolved": unresolved[:3]}
