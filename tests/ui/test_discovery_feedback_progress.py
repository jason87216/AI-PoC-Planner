from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ai_poc_planner.ui.runtime as runtime


def test_feedback_submission_exposes_action_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "feedback-progress-project"

    class FakeApi:
        def __init__(self) -> None:
            self.events: list[str] = []

        def get_project_version(self, *_args: object) -> dict[str, object]:
            return {"project_name": "Feedback progress", "phase": "interview"}

        def profile_status(self, *_args: object) -> dict[str, object]:
            return {"formal_analysis_allowed": True}

        def submit_understanding_feedback(self, *_args: object) -> dict[str, str]:
            self.events.append("submit_understanding_feedback")
            return {"status": "accepted"}

        def generate_understanding(self, *_args: object) -> dict[str, str]:
            self.events.append("generate_understanding")
            return {"status": "generated"}

    fake = FakeApi()
    monkeypatch.setattr(runtime, "get_api_client", lambda: fake)
    monkeypatch.setattr(
        runtime,
        "load_discovery_session",
        lambda *_args: {
            "status": "awaiting_understanding_confirmation",
            "latest_understanding_message_id": "understanding-1",
            "current_round": 1,
        },
    )
    monkeypatch.setattr(
        runtime,
        "load_projects",
        lambda: [
            {
                "project_id": project_id,
                "version_number": 1,
                "project_name": "Feedback progress",
            }
        ],
    )
    monkeypatch.setattr(
        runtime,
        "load_profiles",
        lambda: [
            {
                "id": "profile-1",
                "profile_name": "Test",
                "model_name": "model",
                "is_enabled": True,
            }
        ],
    )
    monkeypatch.setattr(
        runtime,
        "load_visible_messages",
        lambda *_args: [{"id": "understanding-1", "content": "Summary"}],
    )
    monkeypatch.setattr(runtime, "refresh_api_data", lambda: None)

    app = AppTest.from_file(str(Path("app_pages/discovery.py")))
    app.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": 1,
    }
    app.session_state["show_feedback"] = True
    app.run(timeout=10)

    assert not app.exception
    app.text_area[-1].set_value("Please clarify the goal")
    app.button[-1].click()
    app.run(timeout=10)

    assert not app.exception
    assert fake.events == ["submit_understanding_feedback", "generate_understanding"]
    assert app.status
    assert app.status[0].state == "complete"
