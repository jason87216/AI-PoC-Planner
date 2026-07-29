# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from ai_poc_planner.providers.base import StructuredOutputMode
from ai_poc_planner.providers.capabilities import OpenAICompatibleCapabilities
from ai_poc_planner.providers.errors import (
    ProviderOperation,
    ProviderOperationError,
    SafeProviderFailure,
)
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleProviderError
from ai_poc_planner.providers.structured_output import (
    StructuredOutputContentError,
    StructuredOutputExecutor,
)


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class ValueContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


class UnionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int | str


class RecordingAdapter:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[str] = []

    def complete(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: object,
        reasoning_effort: object = None,
    ) -> str:
        del messages, temperature, max_tokens, reasoning_effort
        mode = response_format.as_request_value()["type"]
        self.calls.append(mode)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return str(outcome)


def _caps(
    *, schema: bool = True, object_mode: bool = True
) -> OpenAICompatibleCapabilities:
    return OpenAICompatibleCapabilities(json_schema=schema, json_object=object_mode)


def _execute(
    adapter: RecordingAdapter,
    *,
    preferred: StructuredOutputMode = StructuredOutputMode.JSON_SCHEMA,
    contract: type[BaseModel] = Probe,
    capabilities: OpenAICompatibleCapabilities | None = None,
):
    return StructuredOutputExecutor().execute(
        adapter=adapter,
        capabilities=capabilities or _caps(),
        preferred_mode=preferred,
        operation=ProviderOperation.READINESS,
        schema_name="connection_probe",
        provider_contract=contract,
        messages=[{"role": "user", "content": "probe"}],
        logical_max_tokens=64,
        temperature=0,
    )


def test_schema_first_success_uses_one_call_and_records_metadata() -> None:
    adapter = RecordingAdapter(['{"status":"ok"}'])

    result = _execute(adapter)

    assert adapter.calls == ["json_schema"]
    assert result.mode_used is StructuredOutputMode.JSON_SCHEMA
    assert result.attempt_count == 1
    assert result.fallback_used is False
    assert result.value.status == "ok"


def test_object_first_success_uses_object_mode() -> None:
    adapter = RecordingAdapter(['{"status":"ok"}'])

    result = _execute(adapter, preferred=StructuredOutputMode.JSON_OBJECT)

    assert adapter.calls == ["json_object"]
    assert result.mode_used is StructuredOutputMode.JSON_OBJECT


@pytest.mark.parametrize(
    "bad_content",
    ["not json", "[1]", 'prefix {"status":"ok"}', '```json\n{"status":"ok"}'],
)
def test_invalid_content_repairs_once_without_switching_mode(bad_content: str) -> None:
    adapter = RecordingAdapter([bad_content, '{"status":"ok"}'])

    result = _execute(adapter)

    assert adapter.calls == ["json_schema", "json_schema"]
    assert result.attempt_count == 2


def test_schema_rejection_falls_back_once_to_object() -> None:
    adapter = RecordingAdapter(
        [
            OpenAICompatibleProviderError("provider_structured_output_unsupported"),
            '{"status":"ok"}',
        ]
    )

    result = _execute(adapter)

    assert adapter.calls == ["json_schema", "json_object"]
    assert result.mode_used is StructuredOutputMode.JSON_OBJECT
    assert result.fallback_used is True
    assert result.attempt_count == 2


def test_schema_rejection_object_invalid_then_object_repair() -> None:
    adapter = RecordingAdapter(
        [
            OpenAICompatibleProviderError("provider_structured_output_unsupported"),
            "not json",
            '{"status":"ok"}',
        ]
    )

    result = _execute(adapter)

    assert adapter.calls == ["json_schema", "json_object", "json_object"]
    assert result.attempt_count == 3
    assert result.fallback_used is True


def test_schema_rejection_without_object_support_does_not_retry() -> None:
    adapter = RecordingAdapter(
        [OpenAICompatibleProviderError("provider_structured_output_unsupported")]
    )

    with pytest.raises(ProviderOperationError) as error:
        _execute(adapter, capabilities=_caps(schema=True, object_mode=False))

    assert adapter.calls == ["json_schema"]
    assert error.value.code == "provider_structured_output_unsupported"


@pytest.mark.parametrize(
    "code",
    [
        "provider_http_error",
        "provider_auth_failed",
        "provider_timeout",
        "provider_rate_limited",
    ],
)
def test_transport_failures_do_not_fallback_or_repair(code: str) -> None:
    adapter = RecordingAdapter([OpenAICompatibleProviderError(code)])

    with pytest.raises(ProviderOperationError) as error:
        _execute(adapter)

    assert adapter.calls == ["json_schema"]
    assert error.value.code == code


def test_pydantic_failure_repairs_in_same_mode() -> None:
    adapter = RecordingAdapter(['{"value":"wrong"}', '{"value":3}'])

    result = _execute(adapter, contract=ValueContract)

    assert adapter.calls == ["json_schema", "json_schema"]
    assert result.value.value == 3


def test_provider_invalid_response_and_truncation_repair_once() -> None:
    adapter = RecordingAdapter(
        [
            OpenAICompatibleProviderError("provider_output_truncated"),
            '{"status":"ok"}',
        ]
    )

    result = _execute(adapter)

    assert adapter.calls == ["json_schema", "json_schema"]
    assert result.attempt_count == 2


def test_local_schema_normalization_failure_makes_zero_provider_calls() -> None:
    adapter = RecordingAdapter(['{"value":1}'])

    with pytest.raises(StructuredOutputContentError):
        _execute(adapter, contract=UnionContract)

    assert adapter.calls == []


def test_executor_does_not_run_domain_semantic_validation() -> None:
    adapter = RecordingAdapter(['{"status":"ok"}'])

    result = _execute(adapter)

    assert result.value.status == "ok"


def test_safe_provider_failure_is_immutable_and_secret_free() -> None:
    failure = SafeProviderFailure.from_code(
        "provider_unavailable", ProviderOperation.READINESS
    )
    marker = "raw-provider-marker-p72a"

    assert marker not in str(failure)
    assert marker not in repr(failure)
    with pytest.raises(ValidationError):
        failure.retryable = False
    with pytest.raises(ValidationError):
        SafeProviderFailure(
            code="provider_unavailable",
            operation=ProviderOperation.READINESS,
            retryable=True,
            user_action=f"{marker}",
        )
