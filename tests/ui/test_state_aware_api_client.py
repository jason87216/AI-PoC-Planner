from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.recovery import (
    STATE_RELOAD_ACTION,
    RecoveryAction,
    RecoveryOperation,
    StateAwareApiClient,
    recovery_action_for_status,
)

PROJECT_ID = "10000000-0000-0000-0000-000000000001"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> StateAwareApiClient:
    return StateAwareApiClient(
        client=httpx.Client(
            base_url="http://planner.test",
            transport=httpx.MockTransport(handler),
        )
    )


@pytest.mark.parametrize(
    ("operation", "status", "expected"),
    [
        ("analysis", "ready_for_assessment", RecoveryAction.RETRY_ANALYSIS),
        ("analysis", "assessed", RecoveryAction.CONTINUE_REPORT_ONLY),
        ("analysis", "proposal_generated", RecoveryAction.OPEN_PERSISTED_RESULT),
        ("analysis", "complete", RecoveryAction.OPEN_PERSISTED_RESULT),
        ("analysis", "failed", RecoveryAction.FAIL_CLOSED),
        ("report", "assessed", RecoveryAction.RETRY_REPORT_ONLY),
        ("report", "proposal_generated", RecoveryAction.OPEN_PERSISTED_RESULT),
        ("report", "complete", RecoveryAction.OPEN_PERSISTED_RESULT),
        ("report", "ready_for_assessment", RecoveryAction.FAIL_CLOSED),
    ],
)
def test_recovery_action_uses_only_persisted_status(
    operation: str, status: str, expected: RecoveryAction
) -> None:
    assert recovery_action_for_status(RecoveryOperation(operation), status) is expected


def test_analysis_timeout_after_commit_continues_report_without_replaying_analysis() -> (
    None
):
    status = "ready_for_assessment"
    requests: list[tuple[str, str]] = []
    analysis_posts = 0
    report_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status, analysis_posts, report_posts
        requests.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": status})
        if request.method == "POST" and request.url.path.endswith("/analysis"):
            analysis_posts += 1
            status = "assessed"
            raise httpx.ReadTimeout("response lost after commit", request=request)
        if request.method == "GET" and request.url.path.endswith("/analysis"):
            return httpx.Response(200, json={"id": "analysis-1"})
        if request.method == "POST" and request.url.path.endswith("/report"):
            report_posts += 1
            status = "complete"
            return httpx.Response(201, json={"id": "report-1"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    assert api.create_analysis(PROJECT_ID, 1) == {"id": "analysis-1"}
    assert api.create_report(PROJECT_ID, 1) == {"id": "report-1"}
    assert analysis_posts == 1
    assert report_posts == 1
    assert (
        requests.count(("POST", f"/v1/projects/{PROJECT_ID}/versions/1/analysis")) == 1
    )


def test_analysis_timeout_without_commit_is_retryable_and_never_calls_report() -> None:
    analysis_posts = 0
    report_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal analysis_posts, report_posts
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": "ready_for_assessment"})
        if request.method == "POST" and request.url.path.endswith("/analysis"):
            analysis_posts += 1
            raise httpx.ReadTimeout("no commit", request=request)
        if request.method == "POST" and request.url.path.endswith("/report"):
            report_posts += 1
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    with pytest.raises(ApiClientError) as caught:
        api.create_analysis(PROJECT_ID, 1)

    assert caught.value.code == "local_service_timeout"
    assert caught.value.retryable is True
    assert caught.value.user_action == STATE_RELOAD_ACTION
    assert analysis_posts == 1
    assert report_posts == 0


def test_stale_complete_page_reads_results_without_write_calls() -> None:
    analysis_posts = 0
    report_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal analysis_posts, report_posts
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": "complete"})
        if request.method == "GET" and request.url.path.endswith("/analysis"):
            return httpx.Response(200, json={"id": "analysis-1"})
        if request.method == "GET" and request.url.path.endswith("/report"):
            return httpx.Response(200, json={"id": "report-1"})
        if request.method == "POST" and request.url.path.endswith("/analysis"):
            analysis_posts += 1
        if request.method == "POST" and request.url.path.endswith("/report"):
            report_posts += 1
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    assert api.create_analysis(PROJECT_ID, 1)["id"] == "analysis-1"
    assert api.create_report(PROJECT_ID, 1)["id"] == "report-1"
    assert analysis_posts == 0
    assert report_posts == 0


def test_report_timeout_after_commit_reads_persisted_report_without_replay() -> None:
    status = "assessed"
    report_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status, report_posts
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": status})
        if request.method == "POST" and request.url.path.endswith("/report"):
            report_posts += 1
            status = "complete"
            raise httpx.ReadTimeout("response lost after commit", request=request)
        if request.method == "GET" and request.url.path.endswith("/report"):
            return httpx.Response(200, json={"id": "report-1"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    assert api.create_report(PROJECT_ID, 1) == {"id": "report-1"}
    assert report_posts == 1


def test_report_timeout_without_commit_allows_only_report_retry() -> None:
    report_posts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal report_posts
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": "assessed"})
        if request.method == "POST" and request.url.path.endswith("/report"):
            report_posts += 1
            raise httpx.ReadTimeout("no commit", request=request)
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    with pytest.raises(ApiClientError) as caught:
        api.create_report(PROJECT_ID, 1)

    assert caught.value.code == "local_service_timeout"
    assert caught.value.retryable is True
    assert caught.value.user_action == STATE_RELOAD_ACTION
    assert report_posts == 1


def test_failed_status_fails_closed_without_write() -> None:
    writes = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal writes
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            return httpx.Response(200, json={"status": "failed"})
        if request.method == "POST":
            writes += 1
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    with pytest.raises(ApiClientError) as caught:
        api.create_analysis(PROJECT_ID, 1)

    assert caught.value.code == "persisted_state_conflict"
    assert writes == 0


def test_status_reload_failure_keeps_safe_ambiguous_guidance() -> None:
    version_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal version_reads
        if request.method == "GET" and request.url.path.endswith("/versions/1"):
            version_reads += 1
            if version_reads == 1:
                return httpx.Response(200, json={"status": "ready_for_assessment"})
            raise httpx.ReadTimeout("reload failed", request=request)
        if request.method == "POST" and request.url.path.endswith("/analysis"):
            raise httpx.ReadTimeout("write outcome unknown", request=request)
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    api = _client(handler)

    with pytest.raises(ApiClientError) as caught:
        api.create_analysis(PROJECT_ID, 1)

    assert caught.value.code == "local_service_timeout"
    assert caught.value.retryable is True
    assert caught.value.user_action == STATE_RELOAD_ACTION


def test_streamlit_runtime_factory_uses_state_aware_client() -> None:
    import ai_poc_planner.ui.runtime as runtime

    runtime.get_api_client.clear()
    try:
        client = runtime.get_api_client("http://127.0.0.1:1")
        assert isinstance(client, StateAwareApiClient)
    finally:
        runtime.get_api_client.clear()
