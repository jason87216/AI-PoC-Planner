from __future__ import annotations

import json

import httpx
import pytest

from ai_poc_planner.ui.api_client import StreamlitApiClient, UiApiError


def _client(handler: httpx.MockTransport) -> StreamlitApiClient:
    return StreamlitApiClient(
        "http://planner.test/",
        transport=handler,
    )


def test_client_creates_a_persisted_run() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/planning/runs"
        assert json.loads(request.content) == {
            "natural_language_request": "協助規劃客服 FAQ PoC。",
            "clarification_answers": {},
        }
        return httpx.Response(201, json={"run_id": "run-1", "status": "created"})

    response = _client(httpx.MockTransport(handler)).create_run(
        "協助規劃客服 FAQ PoC。"
    )

    assert response["run_id"] == "run-1"


def test_client_submits_clarification_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/planning/runs/run-1/clarifications"
        assert json.loads(request.content) == {
            "clarification_answers": {"data_classification": "internal"}
        }
        return httpx.Response(200, json={"run_id": "run-1"})

    response = _client(httpx.MockTransport(handler)).submit_clarifications(
        "run-1", {"data_classification": "internal"}
    )

    assert response == {"run_id": "run-1"}


def test_client_reads_a_completed_run() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/planning/runs/run-1"
        return httpx.Response(
            200,
            json={
                "run_id": "run-1",
                "status": "completed",
                "markdown_report": "# 報告",
            },
        )

    response = _client(httpx.MockTransport(handler)).get_run("run-1")

    assert response["status"] == "completed"


def test_client_turns_fastapi_error_envelope_into_a_safe_ui_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": {
                    "code": "planning_run_not_found",
                    "message": "The planning request could not be completed.",
                    "details": {},
                    "correlation_id": "correlation-1",
                }
            },
        )

    with pytest.raises(UiApiError) as error:
        _client(httpx.MockTransport(handler)).get_run("missing")

    assert error.value.code == "planning_run_not_found"
    assert error.value.correlation_id == "correlation-1"
    assert "could not be completed" in error.value.user_message
