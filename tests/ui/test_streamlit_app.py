from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from ai_poc_planner.ui import streamlit_app
from ai_poc_planner.ui.api_client import UiApiError


def test_new_run_replaces_an_existing_interaction_timeline() -> None:
    timeline = streamlit_app.interaction_timeline_for_response(
        [{"title": "舊需求", "content": "第一個 run"}],
        {"original_request": "第二個 run 的新需求"},
        interaction_mode="new_run",
    )

    assert timeline == [{"title": "需求", "content": "第二個 run 的新需求"}]


def test_continuing_a_run_keeps_existing_timeline_and_appends_answers() -> None:
    timeline = streamlit_app.interaction_timeline_for_response(
        [{"title": "需求", "content": "同一個 run"}],
        {"original_request": "不應覆蓋"},
        interaction_mode="continue",
    )
    response = streamlit_app.submit_clarifications_and_append_timeline(
        _SuccessfulClient(),
        "run-1",
        [{"field": "owner", "question": "誰負責？"}],
        {"owner": "客服營運經理"},
        timeline,
    )

    assert response == {"run_id": "run-1", "status": "clarification_required"}
    assert timeline == [
        {"title": "需求", "content": "同一個 run"},
        {"title": "本批補充回答", "content": "誰負責？ → 客服營運經理"},
    ]


def test_failed_clarification_submission_does_not_append_timeline() -> None:
    timeline = [{"title": "需求", "content": "尚未提交"}]

    try:
        streamlit_app.submit_clarifications_and_append_timeline(
            _FailingClient(),
            "run-1",
            [{"field": "owner", "question": "誰負責？"}],
            {"owner": "客服營運經理"},
            timeline,
        )
    except UiApiError:
        pass
    else:
        raise AssertionError("expected UiApiError")

    assert timeline == [{"title": "需求", "content": "尚未提交"}]


class _SuccessfulClient:
    def submit_clarifications(
        self,
        run_id: str,
        clarification_answers: dict[str, object],
    ) -> dict[str, str]:
        assert clarification_answers == {"owner": "客服營運經理"}
        return {"run_id": run_id, "status": "clarification_required"}


class _FailingClient:
    def submit_clarifications(
        self,
        run_id: str,
        clarification_answers: dict[str, object],
    ) -> dict[str, str]:
        raise UiApiError(code="validation_error", user_message="請修正答案")


def test_clarification_answers_use_api_returned_field_names_and_typed_values() -> None:
    answers = streamlit_app.answers_from_form_values(
        [
            {"field": "data_classification"},
            {"field": "external_processing_allowed"},
            {"field": "target_users"},
            {"field": "owner"},
        ],
        {
            "data_classification": "internal",
            "external_processing_allowed": True,
            "target_users": "客服人員\n品質主管",
            "owner": "客服主管",
        },
    )

    assert answers == {
        "data_classification": "internal",
        "external_processing_allowed": True,
        "target_users": ["客服人員", "品質主管"],
        "owner": "客服主管",
    }


def test_markdown_download_payload_is_utf8_bytes() -> None:
    assert streamlit_app.markdown_download_payload("# 規劃報告") == (
        "# 規劃報告".encode()
    )


def test_streamlit_module_has_a_minimal_render_entry_and_respects_boundaries() -> None:
    source = Path(streamlit_app.__file__).read_text(encoding="utf-8")
    app = AppTest.from_file(streamlit_app.__file__).run()

    assert callable(streamlit_app.main)
    assert not app.exception
    assert app.title[0].value == "AI PoC Planner"
    assert "st.caption(f\"Run ID：{response.get('run_id', 'unknown')}\")" in source
    assert 'key="run_id_input"' in source
    assert 'key="current_run_id"' not in source
    assert 'planning_request_draft = ""' not in source
    assert source.count("st.rerun()") == 3
    assert "main_content = st.empty()" in source
    assert source.count("main_content.empty()") == 3
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.agent" not in source
