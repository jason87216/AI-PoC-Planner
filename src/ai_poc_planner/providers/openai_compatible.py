"""Small injected-client adapter for OpenAI-compatible chat completions."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal

import httpx
from pydantic import AnyHttpUrl, Field, SecretStr, TypeAdapter, ValidationError

from ai_poc_planner.domain.models import ContractModel, JSONValue, NonEmptyStr
from ai_poc_planner.providers.base import ProviderError, ReasoningEffort

_HTTP_URL = TypeAdapter(AnyHttpUrl)


class OpenAIChatMessage(ContractModel):
    """A minimal OpenAI-compatible message without tool-call or stream fields."""

    role: Literal["system", "user", "assistant"]
    content: NonEmptyStr


class OpenAIChatCompletionRequest(ContractModel):
    """Validated subset of the OpenAI chat-completions request contract."""

    model: NonEmptyStr
    messages: list[OpenAIChatMessage] = Field(min_length=1)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(ge=1, le=4096)
    response_format: dict[str, JSONValue] | None = None
    reasoning_effort: ReasoningEffort | None = None


class JSONSchemaResponseFormat(ContractModel):
    """OpenAI-compatible structured-output request payload."""

    name: NonEmptyStr
    json_schema: dict[str, JSONValue] = Field(alias="schema")
    strict: bool = True

    def as_request_value(self) -> dict[str, JSONValue]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": self.name,
                "strict": self.strict,
                "schema": self.json_schema,
            },
        }


class JSONObjectResponseFormat(ContractModel):
    """OpenAI-compatible JSON-object mode for contracts with nullable fields.

    The caller still owns complete JSON parsing and Pydantic validation.  This
    mode is an explicit request capability, not a provider-name heuristic.
    """

    def as_request_value(self) -> dict[str, JSONValue]:
        return {"type": "json_object"}


class OpenAICompatibleProviderError(ProviderError):
    """A stable provider code with a safe message and no raw response details."""

    _MESSAGES = {
        "provider_timeout": "The provider connection timed out.",
        "provider_connection_failed": (
            "The provider connection could not be established."
        ),
        "provider_auth_failed": "The provider rejected the connection credentials.",
        "provider_not_found": "The provider endpoint or model was not found.",
        "provider_rate_limited": "The provider is temporarily rate limited.",
        "provider_unavailable": "The provider is temporarily unavailable.",
        "provider_http_error": "The provider request failed.",
        "provider_invalid_response": "The provider returned an invalid response.",
        "provider_output_truncated": "The provider response was truncated.",
    }

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(self._MESSAGES[code])


class OpenAICompatibleChatAdapter:
    """Use an injected ``httpx.Client`` without storing raw provider responses."""

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        api_key: str | None,
        client: httpx.Client,
        timeout_seconds: float = 10,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> None:
        try:
            self._base_url = str(_HTTP_URL.validate_python(base_url)).rstrip("/")
            self._model_name = OpenAIChatCompletionRequest.model_validate(
                {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "validation"}],
                    "temperature": 0,
                    "max_tokens": 1,
                }
            ).model
        except ValidationError as error:
            raise ValueError(
                "invalid OpenAI-compatible adapter configuration"
            ) from error
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._api_key = SecretStr(api_key) if api_key and api_key.strip() else None
        self._client = client
        self._timeout_seconds = timeout_seconds
        self._reasoning_effort = reasoning_effort

    def __repr__(self) -> str:
        key_configured = self._api_key is not None
        return (
            f"{type(self).__name__}(base_url={self._base_url!r}, "
            f"model_name={self._model_name!r}, "
            f"api_key_configured={key_configured})"
        )

    def complete(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: JSONSchemaResponseFormat
        | JSONObjectResponseFormat
        | None = None,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> str:
        try:
            payload = {
                "model": self._model_name,
                "messages": list(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            selected_reasoning_effort = reasoning_effort or self._reasoning_effort
            if selected_reasoning_effort is not None:
                payload["reasoning_effort"] = selected_reasoning_effort
            if response_format is not None:
                payload["response_format"] = response_format.as_request_value()
            request_payload = OpenAIChatCompletionRequest.model_validate(payload)
        except ValidationError as error:
            raise ValueError("invalid chat completion request") from error
        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key.get_secret_value()}"
        try:
            response = self._client.post(
                self._endpoint_url(),
                json=request_payload.model_dump(mode="json", exclude_none=True),
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as error:
            raise OpenAICompatibleProviderError("provider_timeout") from error
        except httpx.RequestError as error:
            raise OpenAICompatibleProviderError("provider_connection_failed") from error
        self._raise_for_http_status(response.status_code)
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as error:
            raise OpenAICompatibleProviderError("provider_invalid_response") from error
        return self._content_from(payload)

    def _endpoint_url(self) -> str:
        suffix = (
            "/chat/completions"
            if self._base_url.endswith(("/v1", "/openai"))
            else "/v1/chat/completions"
        )
        return f"{self._base_url}{suffix}"

    @staticmethod
    def _raise_for_http_status(status_code: int) -> None:
        if 200 <= status_code < 300:
            return
        if status_code in {401, 403}:
            raise OpenAICompatibleProviderError("provider_auth_failed")
        if status_code == 404:
            raise OpenAICompatibleProviderError("provider_not_found")
        if status_code == 429:
            raise OpenAICompatibleProviderError("provider_rate_limited")
        if status_code >= 500:
            raise OpenAICompatibleProviderError("provider_unavailable")
        raise OpenAICompatibleProviderError("provider_http_error")

    @staticmethod
    def _content_from(payload: object) -> str:
        if not isinstance(payload, dict):
            raise OpenAICompatibleProviderError("provider_invalid_response")
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAICompatibleProviderError("provider_invalid_response")
        first = choices[0]
        if not isinstance(first, dict):
            raise OpenAICompatibleProviderError("provider_invalid_response")
        if first.get("finish_reason") == "length":
            raise OpenAICompatibleProviderError("provider_output_truncated")
        message = first.get("message")
        if not isinstance(message, dict):
            raise OpenAICompatibleProviderError("provider_invalid_response")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OpenAICompatibleProviderError("provider_invalid_response")
        return content
