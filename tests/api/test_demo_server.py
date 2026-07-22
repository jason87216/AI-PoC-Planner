from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ai_poc_planner.app.demo_server import create_demo_app


def test_scripted_demo_server_completes_and_can_start_another_run(
    tmp_path: Path,
) -> None:
    client = TestClient(create_demo_app(database_path=tmp_path / "demo.sqlite3"))

    created = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "請協助規劃客服 FAQ PoC。"},
    )

    assert created.status_code == 201
    assert created.json()["status"] == "clarification_required"

    planning_ready = client.post(
        f"/v1/planning/runs/{created.json()['run_id']}/clarifications",
        json={
            "clarification_answers": {
                "data_classification": "internal",
                "external_processing_allowed": True,
                "offline_operation_required": False,
            }
        },
    )

    assert planning_ready.status_code == 200
    assert planning_ready.json()["status"] == "clarification_required"

    completed = client.post(
        f"/v1/planning/runs/{created.json()['run_id']}/clarifications",
        json={
            "clarification_answers": {
                "target_users": ["客服人員"],
                "current_workflow": "先搜尋內部 FAQ，再回覆客戶。",
                "data_sources": ["內部 FAQ"],
                "owner": "客服主管",
            }
        },
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    another_run = client.post(
        "/v1/planning/runs",
        json={"natural_language_request": "再次執行相同展示流程。"},
    )

    assert another_run.status_code == 201
    assert another_run.json()["status"] == "clarification_required"
