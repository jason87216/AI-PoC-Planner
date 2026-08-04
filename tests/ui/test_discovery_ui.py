from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from ai_poc_planner.ui.api_client import ApiClient, ApiClientError
from ai_poc_planner.ui.discovery import (
    discovery_view_for_status,
    facts_summary,
    interview_form_key,
    interview_payload,
    interview_widget_key,
    question_details,
    resolve_interview_answer,
    supplementary_note_key,
)

PROJECT_ID = "10000000-0000-0000-0000-000000000001"
QUESTION_ID = "10000000-0000-0000-0000-000000000002"
FACT_ID = "10000000-0000-0000-0000-000000000003"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> ApiClient:
    return ApiClient(
        client=httpx.Client(
            base_url="http://planner.test",
            transport=httpx.MockTransport(handler),
        )
    )


def test_create_discovery_brief_uses_only_the_formal_contract_fields() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"project": {}, "version": {}, "session": {}})

    api = _client(handler)

    api.create_discovery_project(
        {
            "project_name": "Invoice triage",
            "current_workflow_problem": "Manual routing",
            "desired_outcome": "Faster routing",
            "available_data": "不知道",
            "users_and_owners": "Operations team",
            "known_constraints": "Human review remains required",
        }
    )

    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/v1/discovery-projects")
    ]
    payload = json.loads(requests[0].content)
    assert payload["available_data"] == "不知道"
    assert set(payload) == {
        "project_name",
        "current_workflow_problem",
        "desired_outcome",
        "available_data",
        "users_and_owners",
        "known_constraints",
    }
    assert "supplementary_notes" not in payload


def test_understanding_confirmation_and_correction_use_discovery_endpoints() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "correction_pending"})

    api = _client(handler)

    api.confirm_understanding(PROJECT_ID, 1)
    api.submit_understanding_corrections(
        PROJECT_ID,
        1,
        {
            "corrections": [
                {
                    "target_fact_id": FACT_ID,
                    "status": "confirmed",
                    "value": "Updated workflow",
                    "correction_reason": "The workflow changed",
                }
            ],
            "additional_facts": [],
        },
    )

    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", f"/v1/projects/{PROJECT_ID}/versions/1/understanding/confirm"),
        (
            "POST",
            f"/v1/projects/{PROJECT_ID}/versions/1/understanding/corrections",
        ),
    ]


def test_unknown_answer_and_supplementary_note_use_the_round_contract() -> None:
    payload = interview_payload(
        answers=[
            {"question_id": QUESTION_ID, "answer_status": "unknown", "answer": None}
        ],
        supplementary_note="The finance lead retains approval.",
    )

    assert payload["answers"] == [
        {"question_id": QUESTION_ID, "answer_status": "unknown", "answer": None}
    ]
    assert payload["supplementary_note"] == "The finance lead retains approval."
    assert payload["additional_facts"] == []
    assert payload["corrections"] == []


def test_interview_widget_keys_are_isolated_by_project_version_round_and_question() -> (
    None
):
    first = interview_widget_key("answer", PROJECT_ID, 1, 1, QUESTION_ID)
    second_round = interview_widget_key("answer", PROJECT_ID, 1, 2, QUESTION_ID)
    other_question = interview_widget_key("answer", PROJECT_ID, 1, 1, FACT_ID)
    other_project = interview_widget_key("answer", "other-project", 1, 1, QUESTION_ID)

    assert first == f"interview_answer_{PROJECT_ID}_1_1_{QUESTION_ID}"
    assert len({first, second_round, other_question, other_project}) == 4
    assert interview_form_key(PROJECT_ID, 1, 1) != interview_form_key(PROJECT_ID, 1, 2)
    assert supplementary_note_key(PROJECT_ID, 1, 1) != supplementary_note_key(
        PROJECT_ID, 2, 1
    )
    assert interview_widget_key(
        "status", PROJECT_ID, 1, 1, QUESTION_ID
    ) != interview_widget_key("status", PROJECT_ID, 1, 2, QUESTION_ID)


@pytest.mark.parametrize(
    ("choice", "answer", "expected"),
    [
        ("提供回答", "  正常回答  ", ("answered", "正常回答")),
        ("目前不清楚", "先前輸入的文字", ("unknown", None)),
        ("目前沒有相關資料", "先前輸入的文字", ("missing", None)),
        ("提供回答", "", ("", None)),
    ],
)
def test_interview_choice_is_authoritative_for_answer_payload(
    choice: str, answer: str, expected: tuple[str, str | None]
) -> None:
    assert resolve_interview_answer(choice, answer) == expected


def test_interview_choice_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="unknown interview answer choice"):
        resolve_interview_answer("invalid", "answer")


def test_interview_answer_submission_uses_the_formal_round_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "ready_for_next_round"})

    api = _client(handler)
    api.submit_interview_answers(
        PROJECT_ID,
        1,
        interview_payload(
            answers=[
                {
                    "question_id": QUESTION_ID,
                    "answer_status": "unknown",
                    "answer": None,
                }
            ]
        ),
    )

    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", f"/v1/projects/{PROJECT_ID}/versions/1/interview-answers")
    ]


@pytest.mark.parametrize(
    ("status", "expected_view"),
    [
        ("brief_submitted", "understanding_generation"),
        ("correction_pending", "understanding_generation"),
        ("awaiting_understanding_confirmation", "understanding_confirmation"),
        ("ready_for_interview", "next_round"),
        ("ready_for_next_round", "next_round"),
        ("awaiting_answers", "interview_answers"),
        ("ready_for_assessment", "complete"),
    ],
)
def test_api_discovery_status_alone_selects_the_visible_flow_step(
    status: str, expected_view: str
) -> None:
    assert discovery_view_for_status(status) == expected_view


def test_question_and_fact_summaries_show_only_user_facing_fields() -> None:
    details = question_details(
        {
            "question": "How many requests arrive daily?",
            "why_it_matters": "It affects sizing.",
            "affected_judgement": "Data readiness",
            "example": "A rough range is enough.",
            "id": QUESTION_ID,
        }
    )
    summary = facts_summary(
        [
            {
                "fact_key": "users_and_owners",
                "status": "confirmed",
                "value": "Operations",
            },
            {"fact_key": "available_data", "status": "unknown", "value": None},
            {
                "fact_key": "clarification_round_2_question_1",
                "status": "missing",
                "value": None,
            },
        ]
    )

    assert details == {
        "question": "How many requests arrive daily?",
        "why_it_matters": "It affects sizing.",
        "affected_judgement": "Data readiness",
        "example": "A rough range is enough.",
    }
    assert summary["confirmed"] == ["使用者與負責人：Operations"]
    assert summary["unresolved"] == ["現有資料與文件"]


def test_discovery_errors_are_safe_for_provider_and_stale_state_failures() -> None:
    api = _client(
        lambda _: httpx.Response(
            409,
            json={
                "error": {
                    "code": "interview_question_already_answered",
                    "message": "raw provider detail at http://private.test",
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.list_interview_questions(PROJECT_ID, 1)

    assert caught.value.code == "interview_question_already_answered"
    assert "private.test" not in caught.value.user_message


def test_discovery_ui_hides_fact_governance_and_forbidden_imports() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "discovery.py").read_text(encoding="utf-8")

    assert "target_fact_id" not in source
    assert "回答方式" not in source
    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.providers" not in source


def test_discovery_has_no_second_project_creation_flow() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "discovery.py").read_text(encoding="utf-8")

    assert "_legacy_brief" not in source
    assert "_provider_ready" not in source
    assert 'st.form("create_project")' not in source
    assert "建立專案並整理需求" not in source
    assert "尚未選取專案" in source
    assert "前往新建專案" in source
    assert "前往專案歷史" in source
    assert "discovery_create_mode" not in source
    assert "discovery_return_target" not in source


def test_new_project_route_is_independent_of_discovery_session_flags() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "new_project.py").read_text(encoding="utf-8")

    assert "新建專案" in source
    assert "model_profile_id" in source
    assert "測試模型可用性" in source
    assert "default_profile_index" in source
    assert "is_selected" in source
    assert "discovery_create_mode" not in source
    assert "discovery_return_target" not in source
    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.providers" not in source


def test_discovery_page_keeps_project_context_and_inline_question_generation() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "discovery.py").read_text(encoding="utf-8")

    assert "st.title(project_name)" in source
    assert 'f"第 {version_number} 版 · {phase}"' in source
    assert 'st.title("建立新專案")' in source
    assert 'st.title("新建專案")' not in source
    assert "st.container(border=True)" in source
    assert '"確認",' in source
    assert '"修改",' in source
    assert "理解正確，繼續" not in source
    assert "開始下一輪訪談" not in source
    assert source.index("confirm_understanding") < source.index(
        "generate_interview_round"
    )
    assert "需求理解已確認，但問題尚未生成。" in source
    assert "重新產生訪談問題" in source


def test_discovery_page_generates_the_next_round_after_answers() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "discovery.py").read_text(encoding="utf-8")

    submission = source.index("submit_interview_answers")
    next_generation = source.index("generate_interview_round", submission)
    assert submission < next_generation
    assert "正在整理需要進一步確認的重點……" in source


def test_history_maps_project_statuses_to_safe_actions() -> None:
    root = Path(__file__).parents[2]
    source = (root / "app_pages" / "history.py").read_text(encoding="utf-8")

    assert '"assessed": ("繼續生成報告", "results")' in source
    assert '"complete": ("查看報告", "results")' in source
    assert '"繼續修改", "workspace"' in source
    assert '"複製並修改"' in source
    assert '"複製為新專案"' in source
    assert '"刪除專案"' in source
    assert "raw" not in source.lower()
