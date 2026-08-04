"""Pure, confirmed-only copy preparation for project UIs."""

from __future__ import annotations

_BRIEF_KEYS = {
    "current_workflow_problem": "new_project_current",
    "desired_outcome": "new_project_outcome",
    "available_data": "new_project_data",
    "users_and_owners": "new_project_owners",
    "known_constraints": "new_project_constraints",
}


def build_project_copy_prefill(
    project_name: str, facts: list[dict[str, object]]
) -> dict[str, object]:
    """Build the new-project widget state without copying internal records."""

    values: dict[str, object] = {}
    for fact in facts:
        if fact.get("status") != "confirmed":
            continue
        fact_key = str(fact.get("fact_key") or "")
        target_key = _BRIEF_KEYS.get(fact_key)
        if target_key is None:
            continue
        value = fact.get("value")
        values[target_key] = value if isinstance(value, str) else ""

    return {
        "new_project_name": f"{project_name}（複製）",
        "new_project_current": values.get("new_project_current", ""),
        "new_project_outcome": values.get("new_project_outcome", ""),
        "new_project_data": values.get("new_project_data", ""),
        "new_project_owners": values.get("new_project_owners", ""),
        "new_project_constraints": values.get("new_project_constraints", ""),
    }
