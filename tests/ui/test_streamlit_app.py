from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from ai_poc_planner.ui import streamlit_app


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
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.agent" not in source
