from __future__ import annotations

from types import SimpleNamespace

import pytest

import ai_poc_planner.ui.navigation as navigation


def test_first_entry_and_page_change_show_feedback_but_same_page_rerun_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr(navigation, "st", fake_streamlit)

    assert navigation.transition_for_page("home") == (True, "正在開啟首頁……")
    navigation.finish_page_render("home")
    assert navigation.transition_for_page("home") == (False, "")

    fake_streamlit.session_state[navigation._NAVIGATION_PENDING_KEY] = {
        "page_key": "history",
        "label": "正在開啟專案歷史……",
    }
    assert navigation.transition_for_page("history") == (
        True,
        "正在開啟專案歷史……",
    )
    navigation.finish_page_render("history")
    assert fake_streamlit.session_state[navigation._STABLE_PAGE_KEY] == "history"
    assert navigation.transition_for_page("history") == (False, "")


def test_switch_page_marks_destination_before_public_streamlit_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    fake_streamlit = SimpleNamespace(
        session_state={},
        switch_page=lambda path, **kwargs: calls.append((path, kwargs)),
    )
    monkeypatch.setattr(navigation, "st", fake_streamlit)

    navigation.switch_page(
        "app_pages/results.py",
        query_params={"workspace": "safe-key"},
    )

    assert calls == [
        ("app_pages/results.py", {"query_params": {"workspace": "safe-key"}})
    ]
    assert fake_streamlit.session_state[navigation._NAVIGATION_PENDING_KEY] == {
        "page_key": "project-results",
        "label": "正在開啟評估報告……",
    }


def test_interrupted_source_render_keeps_pending_until_destination() -> None:
    state = {
        navigation._STABLE_PAGE_KEY: "home",
        navigation._NAVIGATION_PENDING_KEY: {
            "page_key": "history",
            "label": "正在開啟專案歷史……",
        },
    }
    fake_streamlit = SimpleNamespace(session_state=state)

    original = navigation.st
    navigation.st = fake_streamlit
    try:
        navigation.finish_page_render("home")
        assert navigation._NAVIGATION_PENDING_KEY in state
        navigation.finish_page_render("history")
    finally:
        navigation.st = original

    assert navigation._NAVIGATION_PENDING_KEY not in state
    assert state[navigation._STABLE_PAGE_KEY] == "history"


def test_page_error_cleanup_can_finish_destination_transition() -> None:
    state = {
        navigation._NAVIGATION_PENDING_KEY: {
            "page_key": "project",
            "label": "正在開啟專案……",
        }
    }
    fake_streamlit = SimpleNamespace(session_state=state)
    original = navigation.st
    navigation.st = fake_streamlit
    try:
        navigation.finish_page_render("project")
    finally:
        navigation.st = original

    assert navigation._NAVIGATION_PENDING_KEY not in state
