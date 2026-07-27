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

CREATE_MODE_KEY = "discovery_create_mode"
RETURN_TARGET_KEY = "discovery_return_target"
_ACTIVE_WIDGET_KEYS = (
    "feedback_text",
    "show_feedback",
    "question_generation_pending",
    "supplementary_note",
)


def is_create_project_mode(state: Mapping[str, Any]) -> bool:
    return state.get(CREATE_MODE_KEY) is True


def enter_create_project_mode(state: MutableMapping[str, Any]) -> None:
    target = state.get("selected_project")
    if isinstance(target, dict):
        state[RETURN_TARGET_KEY] = dict(target)
    state[CREATE_MODE_KEY] = True
    state.pop("selected_project", None)
    for key in tuple(state):
        if key in _ACTIVE_WIDGET_KEYS or key.startswith(
            ("question_", "unknown_", "missing_", "brief_")
        ):
            state.pop(key, None)


def select_active_project(
    state: MutableMapping[str, Any], project_id: str, version_number: int
) -> None:
    state["selected_project"] = {
        "project_id": project_id,
        "version_number": version_number,
    }
    state.pop(CREATE_MODE_KEY, None)
    state.pop(RETURN_TARGET_KEY, None)


def restore_active_project(state: MutableMapping[str, Any]) -> bool:
    target = state.get(RETURN_TARGET_KEY)
    if not isinstance(target, dict):
        return False
    project_id, version_number = target.get("project_id"), target.get("version_number")
    if not isinstance(project_id, str) or not isinstance(version_number, int):
        return False
    select_active_project(state, project_id, version_number)
    return True


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
