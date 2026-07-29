from __future__ import annotations

import json

import httpx
import pytest

from ai_poc_planner.providers.capabilities import (
    AuthenticationMode,
    OpenAICompatibleCapabilities,
    ReasoningParameter,
    TokenParameter,
)
from ai_poc_planner.providers.openai_compatible import (
    JSONObjectResponseFormat,
    JSONSchemaResponseFormat,
    OpenAIChatCompletionRequest,
    OpenAICompatibleChatAdapter,
    OpenAICompatibleProviderError,
)

SECRET_MARKER = "adapter-secret-marker-8d2f6c31"


def _adapter(
    handler: httpx.MockTransport.Handler,
    *,
    base_url: str = "http://localhost:8080",
    api_key: str | None = SECRET_MARKER,
    capabilities: OpenAICompatibleCapabilities | None = None,
    reasoning_effort: str | None = None,
) -> OpenAICompatibleChatAdapter:
    return OpenAICompatibleChatAdapter(
        base_url=base_url,
        model_name="qwen-local",
        api_key=api_key,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        timeout_seconds=1,
        capabilities=capabilities,
        reasoning_effort=reasoning_effort,
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
        (
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            "/v1beta/openai/chat/completions",
        ),
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


def test_adapter_sends_structured_response_format_only_when_requested() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
        response_format=JSONSchemaResponseFormat(
            name="probe",
            schema={
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["ok"]}},
                "required": ["status"],
                "additionalProperties": False,
            },
        ),
    )

    assert json.loads(seen[0].content)["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "probe",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["ok"]}},
                "required": ["status"],
                "additionalProperties": False,
            },
        },
    }
    assert seen[0].headers["Authorization"] == f"Bearer {SECRET_MARKER}"


def test_adapter_sends_explicit_json_object_mode() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
        response_format=JSONObjectResponseFormat(),
    )

    assert json.loads(seen[0].content)["response_format"] == {"type": "json_object"}


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


def test_bearer_required_sends_header_and_rejects_missing_key() -> None:
    capabilities = OpenAICompatibleCapabilities(
        authentication=AuthenticationMode.BEARER_REQUIRED,
        json_schema=True,
        json_object=True,
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler, capabilities=capabilities).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )
    assert seen[0].headers["Authorization"] == f"Bearer {SECRET_MARKER}"

    with pytest.raises(ValueError, match="model_profile_auth_required"):
        _adapter(handler, api_key=None, capabilities=capabilities)


def test_authentication_none_never_sends_header_and_rejects_key() -> None:
    capabilities = OpenAICompatibleCapabilities(
        authentication=AuthenticationMode.NONE,
        json_schema=True,
        json_object=True,
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler, api_key=None, capabilities=capabilities).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )
    assert "Authorization" not in seen[0].headers
    with pytest.raises(ValueError, match="model_profile_auth_forbidden"):
        _adapter(handler, capabilities=capabilities)


@pytest.mark.parametrize(
    ("token_parameter", "expected_field"),
    [
        (TokenParameter.MAX_TOKENS, "max_tokens"),
        (TokenParameter.MAX_COMPLETION_TOKENS, "max_completion_tokens"),
    ],
)
def test_adapter_maps_logical_budget_to_one_token_parameter(
    token_parameter: TokenParameter,
    expected_field: str,
) -> None:
    seen: list[httpx.Request] = []
    capabilities = OpenAICompatibleCapabilities(
        token_parameter=token_parameter,
        json_schema=True,
        json_object=True,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(handler, capabilities=capabilities).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )
    payload = json.loads(seen[0].content)
    assert payload[expected_field] == 12
    assert {"max_tokens", "max_completion_tokens"}.intersection(payload) == {
        expected_field
    }


def test_request_contract_requires_exactly_one_token_parameter() -> None:
    base = {
        "model": "model",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0,
    }
    with pytest.raises(ValueError):
        OpenAIChatCompletionRequest.model_validate(base)
    with pytest.raises(ValueError):
        OpenAIChatCompletionRequest.model_validate(
            {**base, "max_tokens": 1, "max_completion_tokens": 1}
        )


def test_reasoning_parameter_is_capability_driven() -> None:
    seen: list[httpx.Request] = []
    capabilities = OpenAICompatibleCapabilities(
        reasoning_parameter=ReasoningParameter.REASONING_EFFORT,
        json_schema=True,
        json_object=True,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _success(request)

    _adapter(
        handler,
        capabilities=capabilities,
        reasoning_effort="low",
    ).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
    )
    assert json.loads(seen[0].content)["reasoning_effort"] == "low"

    seen.clear()
    unsupported = OpenAICompatibleCapabilities(
        reasoning_parameter=ReasoningParameter.UNSUPPORTED,
        json_schema=True,
        json_object=True,
    )
    _adapter(handler, capabilities=unsupported).complete(
        messages=[{"role": "user", "content": "hello"}],
        temperature=0,
        max_tokens=12,
        reasoning_effort="low",
    )
    assert "reasoning_effort" not in json.loads(seen[0].content)


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (
            {"error": {"message": "response_format json_schema is not supported"}},
            "provider_structured_output_unsupported",
        ),
        (
            {"error": {"message": "response_format value is invalid"}},
            "provider_structured_output_unsupported",
        ),
        (
            {"error": {"message": "max_completion_tokens is unsupported"}},
            "provider_parameter_unsupported",
        ),
        (
            {"error": {"message": "request is invalid"}},
            "provider_http_error",
        ),
    ],
)
def test_client_rejection_classifier_is_narrow_and_safe(
    payload: object,
    expected_code: str,
) -> None:
    raw_marker = "raw-provider-marker-compat-2a"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=payload, headers={"X-Trace": raw_marker})

    with pytest.raises(OpenAICompatibleProviderError) as error:
        _adapter(handler).complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )
    assert error.value.code == expected_code
    assert raw_marker not in str(error.value)


def test_finish_reason_length_is_stable_truncation_error() -> None:
    with pytest.raises(OpenAICompatibleProviderError) as error:
        _adapter(
            lambda _: httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {"content": "{"},
                        }
                    ]
                },
            )
        ).complete(
            messages=[{"role": "user", "content": "hello"}],
            temperature=0,
            max_tokens=12,
        )
    assert error.value.code == "provider_output_truncated"


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
