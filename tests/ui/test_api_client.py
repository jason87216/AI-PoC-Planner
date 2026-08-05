from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from ai_poc_planner.ui.api_client import ApiClient, ApiClientError
from ai_poc_planner.ui.presentation import profile_options


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> ApiClient:
    return ApiClient(
        client=httpx.Client(
            base_url="http://planner.test",
            transport=httpx.MockTransport(handler),
        )
    )


def test_history_and_status_use_only_the_public_http_api() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/projects":
            return httpx.Response(
                200,
                json=[
                    {
                        "project_id": "10000000-0000-0000-0000-000000000001",
                        "project_name": "Invoice triage",
                        "version_number": 2,
                        "status": "assessed",
                        "created_at": "2026-07-25T00:00:00Z",
                        "updated_at": "2026-07-25T01:00:00Z",
                        "completed_at": None,
                        "profile_name": "NVIDIA",
                        "model_name": "openai/gpt-oss-20b",
                    }
                ],
            )
        if request.url.path == "/v1/provider-status":
            return httpx.Response(
                200,
                json={
                    "profile_id": "10000000-0000-0000-0000-000000000002",
                    "connection_state": "connected",
                    "tested_at": "2026-07-25T01:00:00Z",
                    "user_message": "Connection succeeded.",
                    "model_name": "openai/gpt-oss-20b",
                    "formal_analysis_allowed": True,
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    api = _client(handler)

    assert api.list_projects()[0]["project_name"] == "Invoice triage"
    assert api.provider_status()["connection_state"] == "connected"
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/v1/projects"),
        ("GET", "/v1/provider-status"),
    ]


def test_runtime_validation_rejects_other_application_and_old_instance() -> None:
    wrong_app = _client(lambda _: httpx.Response(200, json={"application": "other"}))
    with pytest.raises(ApiClientError, match="其他應用程式"):
        wrong_app.validate_runtime("expected")

    old_instance = _client(
        lambda _: httpx.Response(
            200,
            json={
                "application": "ai-poc-planner",
                "api_contract_version": "1",
                "instance_id": "old",
            },
        )
    )
    with pytest.raises(ApiClientError, match="舊的"):
        old_instance.validate_runtime("expected")


def test_client_without_launcher_configuration_never_falls_back_to_port_8000() -> None:
    client = ApiClient()
    with pytest.raises(ApiClientError) as caught:
        client.list_projects()
    assert caught.value.code == "runtime_configuration_missing"


def test_profile_actions_send_safe_public_requests() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/test"):
            return httpx.Response(
                200,
                json={
                    "profile_id": "10000000-0000-0000-0000-000000000002",
                    "connection_state": "connected",
                    "tested_at": "2026-07-25T01:00:00Z",
                    "user_message": "Connection succeeded.",
                    "model_name": "openai/gpt-oss-20b",
                    "formal_analysis_allowed": True,
                },
            )
        return httpx.Response(
            200 if request.method != "POST" else 201,
            json={
                "id": "10000000-0000-0000-0000-000000000002",
                "profile_name": "NVIDIA",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "model_name": "openai/gpt-oss-20b",
                "structured_output_mode": "json_schema",
                "reasoning_effort": "low",
                "is_selected": True,
                "is_enabled": True,
                "created_at": "2026-07-25T00:00:00Z",
                "updated_at": "2026-07-25T01:00:00Z",
            },
        )

    api = _client(handler)

    api.list_profiles()
    api.create_profile(
        {
            "profile_name": "NVIDIA",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "model_name": "openai/gpt-oss-20b",
            "api_key": "entered-only-for-request",
            "is_enabled": True,
        }
    )
    api.update_profile("10000000-0000-0000-0000-000000000002", {"is_enabled": True})
    api.select_profile("10000000-0000-0000-0000-000000000002")
    assert (
        api.test_profile("10000000-0000-0000-0000-000000000002")[
            "formal_analysis_allowed"
        ]
        is True
    )

    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/v1/model-profiles"),
        ("POST", "/v1/model-profiles"),
        ("PATCH", "/v1/model-profiles/10000000-0000-0000-0000-000000000002"),
        ("POST", "/v1/model-profiles/10000000-0000-0000-0000-000000000002/select"),
        ("POST", "/v1/model-profiles/10000000-0000-0000-0000-000000000002/test"),
    ]
    assert json.loads(requests[1].content)["api_key"] == "entered-only-for-request"


def test_delete_project_uses_the_public_archive_boundary() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    api = _client(handler)
    api.delete_project("10000000-0000-0000-0000-000000000001")

    assert [(request.method, request.url.path) for request in requests] == [
        ("DELETE", "/v1/projects/10000000-0000-0000-0000-000000000001")
    ]


def test_safe_error_never_exposes_api_error_payload_or_connection_address() -> None:
    api = _client(
        lambda _: httpx.Response(
            409,
            json={
                "error": {
                    "code": "provider_not_ready",
                    "message": "http://internal.example.test/raw-provider-detail",
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.provider_status()

    assert caught.value.code == "provider_not_ready"
    assert "internal.example.test" not in caught.value.user_message
    assert "raw-provider-detail" not in caught.value.user_message


def test_provider_error_reads_only_whitelisted_safe_details() -> None:
    raw_marker = "raw-provider-marker-ui-p72a"
    api = _client(
        lambda _: httpx.Response(
            503,
            json={
                "error": {
                    "code": "provider_unavailable",
                    "message": raw_marker,
                    "details": {
                        "operation": "analysis",
                        "retryable": True,
                        "user_action": "請稍後重試，並確認服務目前可用。",
                        "raw": raw_marker,
                    },
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.provider_status()

    assert caught.value.retryable is True
    assert caught.value.user_action == "請稍後重試，並確認服務目前可用。"
    assert raw_marker not in str(caught.value)
    assert raw_marker not in repr(caught.value)


def test_generic_provider_http_error_uses_safe_ui_mapping() -> None:
    raw_marker = "raw-provider-http-marker-ui-p72a"
    api = _client(
        lambda _: httpx.Response(
            400,
            json={
                "error": {
                    "code": "provider_http_error",
                    "message": raw_marker,
                    "details": {
                        "operation": "report",
                        "retryable": False,
                        "user_action": "請檢查端點設定與請求能力後再試。",
                        "raw": raw_marker,
                    },
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.provider_status()

    assert caught.value.code == "provider_http_error"
    assert caught.value.user_message != "服務暫時無法完成此操作，請稍後再試。"
    assert caught.value.user_action == "請檢查端點設定與請求能力後再試。"
    assert caught.value.retryable is False
    assert raw_marker not in str(caught.value)
    assert raw_marker not in repr(caught.value)


def test_interview_questions_unavailable_keeps_safe_retry_guidance() -> None:
    api = _client(
        lambda _: httpx.Response(
            502,
            json={
                "error": {
                    "code": "interview_questions_unavailable",
                    "message": "raw provider detail must not surface",
                    "details": {
                        "operation": "discovery",
                        "retryable": True,
                        "user_action": (
                            "請重新產生訪談問題；若持續失敗，請重新測試模型設定並查看"
                            "本機啟動日誌。"
                        ),
                    },
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.generate_interview_round("10000000-0000-0000-0000-000000000001", 1)

    assert caught.value.code == "interview_questions_unavailable"
    assert caught.value.retryable is True
    assert caught.value.user_action == (
        "請重新產生訪談問題；若持續失敗，請重新測試模型設定並查看本機啟動日誌。"
    )
    assert "raw provider detail" not in str(caught.value)


def test_database_failure_has_actionable_safe_ui_guidance() -> None:
    raw_marker = "C:\\private\\planner.sqlite3"
    api = _client(
        lambda _: httpx.Response(
            500,
            json={
                "error": {
                    "code": "database_operation_failed",
                    "message": f"SQL traceback {raw_marker}",
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.list_projects()

    assert "本機資料庫無法初始化或升級" in caught.value.user_message
    assert "重新啟動" in caught.value.user_message
    assert raw_marker not in str(caught.value)


def test_analysis_result_validation_has_actionable_safe_ui_guidance() -> None:
    raw_marker = "raw-provider-analysis-marker"
    api = _client(
        lambda _: httpx.Response(
            502,
            json={
                "error": {
                    "code": "analysis_result_invalid",
                    "message": raw_marker,
                    "details": {
                        "operation": "analysis",
                        "retryable": False,
                        "user_action": (
                            "若持續失敗，請重新測試模型設定；問題仍存在時請查看本機啟動日誌。"
                        ),
                        "raw": raw_marker,
                    },
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.list_projects()

    assert "評估結果格式無法驗證" in caught.value.user_message
    assert (
        caught.value.user_action
        == "若持續失敗，請重新測試模型設定；問題仍存在時請查看本機啟動日誌。"
    )
    assert raw_marker not in str(caught.value)
    assert raw_marker not in repr(caught.value)


def test_analysis_category_mismatch_has_actionable_safe_ui_guidance() -> None:
    raw_marker = "raw-provider-category-marker"
    api = _client(
        lambda _: httpx.Response(
            409,
            json={
                "error": {
                    "code": "solution_category_mismatch",
                    "message": raw_marker,
                    "details": {
                        "operation": "analysis",
                        "retryable": False,
                        "user_action": (
                            "請檢查核准方案目錄與正式評估類別的設定；"
                            "修正後可安全重試評估。"
                        ),
                        "raw": raw_marker,
                    },
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.list_projects()

    assert "正式評估類別與核准方案目錄不一致" in caught.value.user_message
    assert caught.value.user_action == (
        "請檢查核准方案目錄與正式評估類別的設定；修正後可安全重試評估。"
    )
    assert raw_marker not in str(caught.value)
    assert raw_marker not in repr(caught.value)


def test_project_model_binding_sends_only_a_profile_reference() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "10000000-0000-0000-0000-000000000004",
                "project_id": "10000000-0000-0000-0000-000000000001",
                "version_number": 1,
                "status": "draft",
                "selected_model": None,
                "created_at": "2026-07-25T00:00:00Z",
                "updated_at": "2026-07-25T00:00:00Z",
                "completed_at": None,
            },
        )

    api = _client(handler)
    api.bind_project_model_profile(
        "10000000-0000-0000-0000-000000000001",
        1,
        "10000000-0000-0000-0000-000000000002",
    )

    assert requests[0].method == "POST"
    assert requests[0].url.path.endswith("/versions/1/model-profile")
    assert json.loads(requests[0].content) == {
        "model_profile_id": "10000000-0000-0000-0000-000000000002"
    }


def test_natural_language_feedback_uses_the_public_discovery_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "correction_pending"})

    api = _client(handler)
    api.submit_understanding_feedback(
        "10000000-0000-0000-0000-000000000001", 1, "請保留紙本申請。"
    )

    assert [(request.method, request.url.path) for request in requests] == [
        (
            "POST",
            "/v1/projects/10000000-0000-0000-0000-000000000001/versions/1/"
            "understanding/feedback",
        )
    ]
    assert json.loads(requests[0].content) == {"feedback": "請保留紙本申請。"}


def test_profile_options_keep_duplicate_display_names_independently_selectable() -> (
    None
):
    profiles = [
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "profile_name": "NVIDIA",
            "model_name": "openai/gpt-oss-20b",
        },
        {
            "id": "10000000-0000-0000-0000-000000000003",
            "profile_name": "NVIDIA",
            "model_name": "openai/gpt-oss-20b",
        },
    ]

    options = profile_options(profiles)

    assert list(options) == [
        "10000000-0000-0000-0000-000000000002",
        "10000000-0000-0000-0000-000000000003",
    ]


def test_ui_package_does_not_import_application_persistence_or_provider_layers() -> (
    None
):
    from pathlib import Path

    root = Path(__file__).parents[2]
    source_paths = [
        *(root / "src" / "ai_poc_planner" / "ui").rglob("*.py"),
        *(root / "app_pages").rglob("*.py"),
        root / "streamlit_app.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)

    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.providers" not in source
