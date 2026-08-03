from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ai_poc_planner.ui.navigation as navigation
import ai_poc_planner.ui.runtime as runtime


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

    app = AppTest.from_file(str(Path("app_pages/history.py"))).run(timeout=10)

    assert not app.exception
    assert app.button[-1].label == "查看報告"
    app.button[-1].click().run(timeout=10)

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

    app = AppTest.from_file(str(Path("app_pages/results.py")))
    app.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": 1,
    }
    app.run(timeout=10)

    assert not app.exception
    assert any("Persisted complete report" in item.value for item in app.markdown)
    assert not any("生成評估報告" in button.label for button in app.button)
