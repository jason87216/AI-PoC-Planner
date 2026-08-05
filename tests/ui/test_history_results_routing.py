from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ai_poc_planner.ui.navigation as navigation
import ai_poc_planner.ui.runtime as runtime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PAGE = PROJECT_ROOT / "app_pages" / "history.py"
RESULTS_PAGE = PROJECT_ROOT / "app_pages" / "results.py"


def test_history_app_routes_complete_project_to_results_without_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "complete-project"
    projects = [
        {
            "project_id": project_id,
            "version_number": 1,
            "project_name": "Completed project",
            "status": "complete",
            "updated_at": "2026-08-03T00:00:00Z",
        }
    ]
    destinations: list[tuple[str, str, int]] = []

    monkeypatch.setattr(runtime, "load_projects", lambda: projects)
    monkeypatch.setattr(runtime, "refresh_api_data", lambda: None)
    monkeypatch.setattr(
        navigation,
        "open_results",
        lambda selected_id, version: destinations.append(
            ("results", selected_id, version)
        ),
    )
    monkeypatch.setattr(
        navigation,
        "open_workspace",
        lambda selected_id, version: destinations.append(
            ("workspace", selected_id, version)
        ),
    )

    app = AppTest.from_file(str(HISTORY_PAGE)).run(timeout=10)

    assert not app.exception
    labels = {button.label for button in app.button}
    assert {"查看報告", "複製並修改", "確認刪除專案"} <= labels
    report_button = next(button for button in app.button if button.label == "查看報告")
    report_button.click().run(timeout=10)

    assert not app.exception
    assert destinations == [("results", project_id, 1)]


def test_results_app_reads_complete_persisted_report_without_generation_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "complete-project"
    monkeypatch.setattr(
        runtime,
        "load_projects",
        lambda: [
            {
                "project_id": project_id,
                "version_number": 1,
                "project_name": "Completed project",
                "status": "complete",
            }
        ],
    )
    monkeypatch.setattr(
        runtime,
        "load_project_version",
        lambda *_args: {
            "status": "complete",
            "selected_model": {"model_name": "test-model"},
        },
    )
    monkeypatch.setattr(
        runtime,
        "load_report",
        lambda *_args: {"markdown": "Persisted complete report"},
    )

    app = AppTest.from_file(str(RESULTS_PAGE))
    app.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": 1,
    }
    app.run(timeout=10)

    assert not app.exception
    assert any("Persisted complete report" in item.value for item in app.markdown)
    assert not any("生成評估報告" in button.label for button in app.button)


def test_history_unfinished_project_has_workspace_copy_and_delete_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "draft-project"
    monkeypatch.setattr(
        runtime,
        "load_projects",
        lambda: [
            {
                "project_id": project_id,
                "version_number": 1,
                "project_name": "Draft project",
                "status": "draft",
            }
        ],
    )
    monkeypatch.setattr(runtime, "refresh_api_data", lambda: None)
    destinations: list[tuple[str, str, int]] = []
    monkeypatch.setattr(
        navigation,
        "open_workspace",
        lambda selected_id, version: destinations.append(
            ("workspace", selected_id, version)
        ),
    )

    app = AppTest.from_file(str(HISTORY_PAGE)).run(timeout=10)

    assert not app.exception
    labels = {button.label for button in app.button}
    assert {"繼續修改", "複製為新專案", "確認刪除專案"} <= labels
    next(button for button in app.button if button.label == "繼續修改").click().run(
        timeout=10
    )
    assert destinations == [("workspace", project_id, 1)]


def test_results_stale_query_is_closed_without_exposing_internal_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "load_projects", lambda: [])
    app = AppTest.from_file(str(RESULTS_PAGE))
    app.query_params["workspace"] = navigation.workspace_route_key("archived")
    app.query_params["version"] = "1"
    app.run(timeout=10)

    assert not app.exception
    assert any("找不到這個專案，或專案已經刪除。" in item.value for item in app.error)
    assert not any("archive" in item.value.lower() for item in app.markdown)


def test_results_app_recovers_target_from_hashed_query_after_session_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "10000000-0000-0000-0000-000000000099"
    monkeypatch.setattr(
        runtime,
        "load_projects",
        lambda: [
            {
                "project_id": project_id,
                "version_number": 1,
                "project_name": "Query recovered project",
                "status": "complete",
            }
        ],
    )
    monkeypatch.setattr(
        runtime,
        "load_project_version",
        lambda *_args: {
            "status": "complete",
            "selected_model": {"model_name": "test-model"},
        },
    )
    monkeypatch.setattr(
        runtime,
        "load_report",
        lambda *_args: {"markdown": "Query recovered persisted report"},
    )

    app = AppTest.from_file(str(RESULTS_PAGE))
    app.query_params["workspace"] = navigation.workspace_route_key(project_id)
    app.query_params["version"] = "1"
    app.run(timeout=10)

    assert not app.exception
    assert any(
        "Query recovered persisted report" in item.value for item in app.markdown
    )
    assert app.session_state["selected_project"] == {
        "project_id": project_id,
        "version_number": 1,
    }


def test_discovery_report_destinations_keep_explicit_project_query_target() -> None:
    source = Path("app_pages/discovery.py").read_text(encoding="utf-8")

    assert source.count("open_results(project_id, number)") == 2
    assert 'switch_page("app_pages/results.py")' not in source


def test_results_workspace_destination_keeps_explicit_project_query_target() -> None:
    source = Path("app_pages/results.py").read_text(encoding="utf-8")

    assert "open_workspace(project_id, version_number)" in source
    assert 'switch_page("app_pages/discovery.py")' not in source
