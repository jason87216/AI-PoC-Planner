"""One bounded, capability-driven structured-output execution policy."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ValidationError

from ai_poc_planner.providers.base import ProviderError, ReasoningEffort, StructuredOutputMode
from ai_poc_planner.providers.capabilities import OpenAICompatibleCapabilities
from ai_poc_planner.providers.errors import (
    ProviderOperation,
    ProviderOperationError,
    SafeProviderFailure,
)
from ai_poc_planner.providers.json_schema import normalize_provider_schema
from ai_poc_planner.providers.openai_compatible import (
    JSONObjectResponseFormat,
    JSONSchemaResponseFormat,
    OpenAICompatibleProviderError,
)


class StructuredOutputAdapter(Protocol):
    def complete(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: JSONSchemaResponseFormat | JSONObjectResponseFormat,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> str: ...


class StructuredOutputContentError(ProviderError):
    """A bounded content/contract failure with no raw model output attached."""

    def __init__(self, code: str = "provider_output_invalid") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class StructuredOutputExecution:
    """In-memory execution metadata; never persisted or returned as raw output."""

    value: BaseModel
    operation: ProviderOperation
    mode_used: StructuredOutputMode
    attempt_count: int
    fallback_used: bool


_JSON_FENCE = re.compile(r"\A```json\s*(.*?)\s*```\Z", re.DOTALL | re.IGNORECASE)


class StructuredOutputExecutor:
    """Execute one provider contract with one repair and one directed fallback."""

    def execute(
        self,
        *,
        adapter: StructuredOutputAdapter,
        capabilities: OpenAICompatibleCapabilities,
        preferred_mode: StructuredOutputMode,
        operation: ProviderOperation,
        schema_name: str,
        provider_contract: type[BaseModel],
        messages: Sequence[Mapping[str, str]],
        logical_max_tokens: int,
        temperature: float,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> StructuredOutputExecution:
        mode = self._validate_mode(capabilities, preferred_mode, operation)
        schema: dict[str, object] | None = None
        if mode is StructuredOutputMode.JSON_SCHEMA:
            try:
                schema = normalize_provider_schema(
                    provider_contract.model_json_schema()
                )
            except (TypeError, ValueError, KeyError) as error:
                raise StructuredOutputContentError from error

        attempts = 0
        mode_attempts = 0
        fallback_used = False
        while True:
            attempts += 1
            mode_attempts += 1
            try:
                content = self._call(
                    adapter=adapter,
                    mode=mode,
                    schema_name=schema_name,
                    schema=schema,
                    messages=messages,
                    logical_max_tokens=logical_max_tokens,
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                )
                value = self._parse_and_validate(content, provider_contract)
                return StructuredOutputExecution(
                    value=value,
                    operation=operation,
                    mode_used=mode,
                    attempt_count=attempts,
                    fallback_used=fallback_used,
                )
            except OpenAICompatibleProviderError as error:
                if (
                    error.code == "provider_structured_output_unsupported"
                    and mode is StructuredOutputMode.JSON_SCHEMA
                    and capabilities.json_object
                    and not fallback_used
                ):
                    mode = StructuredOutputMode.JSON_OBJECT
                    schema = None
                    fallback_used = True
                    mode_attempts = 0
                    continue
                if error.code in {
                    "provider_invalid_response",
                    "provider_output_truncated",
                } and mode_attempts == 1:
                    messages = self._repair_messages(messages, provider_contract)
                    continue
                raise self._provider_error(error.code, operation) from error
            except StructuredOutputContentError as error:
                if mode_attempts == 1:
                    messages = self._repair_messages(messages, provider_contract)
                    continue
                raise error
            except ProviderOperationError:
                raise
            except ProviderError as error:
                code = getattr(error, "code", "provider_http_error")
                raise self._provider_error(code, operation) from error

    @staticmethod
    def _validate_mode(
        capabilities: OpenAICompatibleCapabilities,
        preferred_mode: StructuredOutputMode,
        operation: ProviderOperation,
    ) -> StructuredOutputMode:
        supported = {
            StructuredOutputMode.JSON_SCHEMA: capabilities.json_schema,
            StructuredOutputMode.JSON_OBJECT: capabilities.json_object,
        }
        if not supported.get(preferred_mode, False):
            raise ProviderOperationError(
                SafeProviderFailure.from_code(
                    "model_profile_structured_output_invalid", operation
                )
            )
        return preferred_mode

    @staticmethod
    def _call(
        *,
        adapter: StructuredOutputAdapter,
        mode: StructuredOutputMode,
        schema_name: str,
        schema: dict[str, object] | None,
        messages: Sequence[Mapping[str, str]],
        logical_max_tokens: int,
        temperature: float,
        reasoning_effort: ReasoningEffort | None,
    ) -> str:
        response_format = (
            JSONSchemaResponseFormat(name=schema_name, schema=schema or {})
            if mode is StructuredOutputMode.JSON_SCHEMA
            else JSONObjectResponseFormat()
        )
        return adapter.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=logical_max_tokens,
            response_format=response_format,
            reasoning_effort=reasoning_effort,
        )

    @staticmethod
    def _parse_and_validate(
        content: str,
        provider_contract: type[BaseModel],
    ) -> BaseModel:
        if not isinstance(content, str) or not content.strip():
            raise StructuredOutputContentError
        candidate = content.strip()
        fenced = _JSON_FENCE.fullmatch(candidate)
        if fenced is not None:
            candidate = fenced.group(1).strip()
        try:
            payload = json.loads(candidate)
        except (TypeError, json.JSONDecodeError) as error:
            raise StructuredOutputContentError from error
        if not isinstance(payload, dict):
            raise StructuredOutputContentError
        try:
            return provider_contract.model_validate(payload)
        except ValidationError as error:
            raise StructuredOutputContentError from error

    @staticmethod
    def _repair_messages(
        messages: Sequence[Mapping[str, str]],
        provider_contract: type[BaseModel],
    ) -> list[dict[str, str]]:
        fields = ", ".join(provider_contract.model_fields)
        prompt = (
            "上一個回應未符合結構化輸出契約。請只回傳一個完整 JSON object，"
            f"不得加入 markdown 或解釋。必要欄位：{fields}。"
        )
        return [
            {"role": str(message["role"]), "content": str(message["content"])}
            for message in messages
        ] + [{"role": "user", "content": prompt}]

    @staticmethod
    def _provider_error(code: str, operation: ProviderOperation) -> ProviderOperationError:
        return ProviderOperationError(SafeProviderFailure.from_code(code, operation))


__all__ = [
    "ProviderOperationError",
    "StructuredOutputContentError",
    "StructuredOutputExecution",
    "StructuredOutputExecutor",
]
