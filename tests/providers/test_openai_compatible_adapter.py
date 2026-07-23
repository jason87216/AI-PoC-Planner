from __future__ import annotations

import json

import httpx
import pytest

from ai_poc_planner.providers.openai_compatible import (
    OpenAICompatibleChatAdapter,
    OpenAICompatibleProviderError,
)

SECRET_MARKER = "adapter-secret-marker-8d2f6c31"


def _adapter(
    handler: httpx.MockTransport.Handler,
    *,
    base_url: str = "http://localhost:8080",
    api_key: str | None = SECRET_MARKER,
) -> OpenAICompatibleChatAdapter:
    return OpenAICompatibleChatAdapter(
        base_url=base_url,
        model_name="qwen-local",
        api_key=api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        timeout_seconds=1,
    )


def _success(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": "connection ok"}}]},
    )


@pytest.mark.parametrize(
    ("base_url", "expected_path"),
    [
        ("http://localhost:8080", "/v1/chat/completions"),
        ("http://localhost:8080/v1", "/v1/chat/completions"),
    ],
)
def test_adapter_joins_openai_endpoint_once(
    base_url: str,
    expected_path: str,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    content = _adapter(handler, base_url=base_url).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )

    assert content == "connection ok"
    assert seen[0].method == "POST"
    assert seen[0].url.path == expected_path
    assert json.loads(seen[0].content) == {
        "model": "qwen-local",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0,
        "max_tokens": 12,
    }
    assert seen[0].headers["Authorization"] == f"Bearer {SECRET_MARKER}"


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_adapter_omits_authorization_for_blank_api_keys(api_key: str | None) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler, api_key=api_key).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )

    assert "Authorization" not in seen[0].headers


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, "provider_auth_failed"),
        (403, "provider_auth_failed"),
        (404, "provider_not_found"),
        (429, "provider_rate_limited"),
        (500, "provider_unavailable"),
    ],
)
def test_adapter_maps_http_failures_without_exposing_response_or_secret(
    status_code: int,
    expected_code: str,
) -> None:
    raw_marker = "provider-body-marker-54ca"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=raw_marker)

    with pytest.raises(OpenAICompatibleProviderError) as error:
        _adapter(handler).complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )

    assert error.value.code == expected_code
    assert raw_marker not in str(error.value)
    assert SECRET_MARKER not in str(error.value)
    assert SECRET_MARKER not in repr(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"choices": "invalid"},
    ],
)
def test_adapter_rejects_invalid_response_schema_without_raw_body(
    payload: object,
) -> None:
    with pytest.raises(OpenAICompatibleProviderError) as error:
        _adapter(lambda _: httpx.Response(200, json=payload)).complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )

    assert error.value.code == "provider_invalid_response"


def test_adapter_maps_invalid_json_and_network_errors() -> None:
    invalid_json = _adapter(lambda _: httpx.Response(200, text="not-json"))
    network = _adapter(
        lambda request: (_ for _ in ()).throw(
            httpx.ConnectError("offline", request=request)
        )
    )

    with pytest.raises(OpenAICompatibleProviderError) as invalid_error:
        invalid_json.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )
    with pytest.raises(OpenAICompatibleProviderError) as network_error:
        network.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )

    assert invalid_error.value.code == "provider_invalid_response"
    assert network_error.value.code == "provider_connection_failed"


def test_adapter_maps_timeout_and_hides_secret_in_repr() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = _adapter(handler)

    with pytest.raises(OpenAICompatibleProviderError) as error:
        adapter.complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )

    assert error.value.code == "provider_timeout"
    assert SECRET_MARKER not in repr(adapter)
