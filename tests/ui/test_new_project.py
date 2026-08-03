from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ai_poc_planner.ui.navigation as navigation
import ai_poc_planner.ui.runtime as runtime
from ai_poc_planner.ui.api_client import ApiClientError

PAGE = str(Path("app_pages/new_project.py"))
PROFILE = {
    "id": "profile-1",
    "profile_name": "Test profile",
    "model_name": "test-model",
    "is_enabled": True,
    "is_selected": True,
}


class FakeApi:
    def __init__(self, *, create_error: bool = False) -> None:
        self.create_error = create_error
        self.created_payloads: list[dict[str, object]] = []

    def profile_status(self, _profile_id: str) -> dict[str, object]:
        return {"formal_analysis_allowed": True}

    def create_discovery_project(self, payload: dict[str, object]) -> dict[str, object]:
        if self.create_error:
            raise ApiClientError(
                "database_operation_failed",
                "本機資料庫無法完成操作。",
            )
        self.created_payloads.append(payload)
        return {
            "project": {"id": "project-new"},
            "version": {"version_number": 1},
        }

    def generate_understanding(self, _project_id: str, _version_number: int) -> None:
        return None


def _prepare_page(monkeypatch: pytest.MonkeyPatch, fake: FakeApi) -> None:
    monkeypatch.setattr(runtime, "get_api_client", lambda: fake)
    monkeypatch.setattr(runtime, "load_profiles", lambda: [PROFILE])
    monkeypatch.setattr(runtime, "refresh_api_data", lambda: None)
    monkeypatch.setattr(navigation, "open_workspace", lambda *_args: None)


def _submit(app: AppTest) -> None:
    next(
        button for button in app.button if button.label == "建立專案並整理需求"
    ).click()


def test_new_project_renders_when_optional_widget_state_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeApi()
    _prepare_page(monkeypatch, fake)
    app = AppTest.from_file(PAGE)
    for key in (
        "new_project_outcome",
        "new_project_data",
        "new_project_owners",
        "new_project_constraints",
    ):
        app.session_state[key] = None

    app.run(timeout=10)

    assert not app.exception
    assert app.text_input[0].value == ""
    assert all(widget.value == "" for widget in app.text_area)


def test_new_project_prefill_none_values_are_blank_and_submit_as_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeApi()
    _prepare_page(monkeypatch, fake)
    app = AppTest.from_file(PAGE)
    app.session_state["new_project_prefill"] = {
        "new_project_name": "Copied project",
        "new_project_current": "Manual workflow",
        "new_project_outcome": None,
        "new_project_data": None,
        "new_project_owners": None,
        "new_project_constraints": None,
    }
    app.run(timeout=10)

    assert not app.exception
    assert app.text_input[0].value == "Copied project"
    assert app.text_area[0].value == "Manual workflow"
    assert all(widget.value == "" for widget in app.text_area[1:])
    assert "None" not in [widget.value for widget in app.text_area]

    _submit(app)
    app.run(timeout=10)

    assert not app.exception
    assert fake.created_payloads[0] == {
        "project_name": "Copied project",
        "current_workflow_problem": "Manual workflow",
        "desired_outcome": None,
        "available_data": None,
        "users_and_owners": None,
        "known_constraints": None,
        "model_profile_id": "profile-1",
    }
    assert all(
        key not in app.session_state
        for key in (
            "new_project_name",
            "new_project_current",
            "new_project_outcome",
            "new_project_data",
            "new_project_owners",
            "new_project_constraints",
        )
    )


def test_new_project_rejects_blank_required_fields_without_api_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeApi()
    _prepare_page(monkeypatch, fake)
    app = AppTest.from_file(PAGE).run(timeout=10)

    _submit(app)
    app.run(timeout=10)

    assert not app.exception
    assert fake.created_payloads == []
    assert any("請填寫專案名稱與目前流程與問題" in item.value for item in app.warning)


def test_new_project_rejects_none_required_widget_state_without_api_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeApi()
    _prepare_page(monkeypatch, fake)
    app = AppTest.from_file(PAGE)
    app.session_state["new_project_name"] = None
    app.session_state["new_project_current"] = None
    app.run(timeout=10)

    assert not app.exception
    assert app.text_input[0].value == ""
    assert app.text_area[0].value == ""
    _submit(app)
    app.run(timeout=10)

    assert not app.exception
    assert fake.created_payloads == []
    assert any("請填寫專案名稱與目前流程與問題" in item.value for item in app.warning)


def test_new_project_api_failure_preserves_form_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeApi(create_error=True)
    _prepare_page(monkeypatch, fake)
    app = AppTest.from_file(PAGE).run(timeout=10)
    app.text_input[0].set_value("Keep this")
    app.text_area[0].set_value("Keep this workflow")
    _submit(app)
    app.run(timeout=10)

    assert not app.exception
    assert app.session_state["new_project_name"] == "Keep this"
    assert app.session_state["new_project_current"] == "Keep this workflow"
