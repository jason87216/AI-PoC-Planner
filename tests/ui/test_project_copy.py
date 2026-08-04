from ai_poc_planner.ui.project_copy import build_project_copy_prefill


def test_project_copy_prefill_only_contains_confirmed_brief_facts() -> None:
    prefill = build_project_copy_prefill(
        "原專案",
        [
            {
                "fact_key": "current_workflow_problem",
                "status": "confirmed",
                "value": "人工整理",
            },
            {"fact_key": "desired_outcome", "status": "missing", "value": None},
            {
                "fact_key": "available_data",
                "status": "unknown",
                "value": "不要複製",
            },
            {
                "fact_key": "users_and_owners",
                "status": "confirmed",
                "value": "客服主管",
            },
            {
                "fact_key": "internal_id",
                "status": "confirmed",
                "value": "不應出現",
            },
        ],
    )

    assert prefill == {
        "new_project_name": "原專案（複製）",
        "new_project_current": "人工整理",
        "new_project_outcome": "",
        "new_project_data": "",
        "new_project_owners": "客服主管",
        "new_project_constraints": "",
    }
