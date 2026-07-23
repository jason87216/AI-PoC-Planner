import json
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_poc_planner.providers import (
    ModelProfile,
    ProviderConnectionMessage,
    ProviderConnectionState,
    ProviderConnectionStatus,
)

PROFILE_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
SPECIAL_API_KEY = "key-with-special-characters:/?&=+%$#[]"
INVALID_API_KEY_MARKER = "invalid-api-key-marker-5f9a4bd2"


def _profile(**overrides: object) -> ModelProfile:
    values: dict[str, object] = {
        "schema_version": "1.0",
        "id": PROFILE_ID,
        "profile_name": "Local llama.cpp",
        "base_url": "http://localhost:8080/v1",
        "model_name": "qwen-local",
        "api_key": SPECIAL_API_KEY,
        "is_selected": True,
        "is_enabled": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return ModelProfile.model_validate(values)


def _status(**overrides: object) -> ProviderConnectionStatus:
    values: dict[str, object] = {
        "schema_version": "1.0",
        "profile_id": PROFILE_ID,
        "connection_state": ProviderConnectionState.CONNECTED,
        "tested_at": NOW,
        "user_message": ProviderConnectionMessage.CONNECTED,
        "model_name": "qwen-local",
    }
    values.update(overrides)
    return ProviderConnectionStatus.model_validate(values)


def test_model_profile_keeps_private_secret_separate_from_public_contract() -> None:
    profile = _profile()

    public_profile = profile.to_public()
    public_json = public_profile.model_dump_json()

    assert profile.api_key is not None
    assert profile.api_key.get_secret_value() == SPECIAL_API_KEY
    assert public_profile.id == PROFILE_ID
    assert "api_key" not in public_profile.model_dump()
    assert SPECIAL_API_KEY not in public_json
    assert SPECIAL_API_KEY not in str(public_profile.model_dump())
    assert SPECIAL_API_KEY not in repr(public_profile.model_dump())
    assert SPECIAL_API_KEY not in profile.model_dump_json()
    assert SPECIAL_API_KEY not in str(profile.model_dump())
    assert SPECIAL_API_KEY not in repr(profile.model_dump())
    assert SPECIAL_API_KEY not in repr(profile)
    assert SPECIAL_API_KEY not in str(profile)


def test_model_profile_round_trips_through_private_and_public_json() -> None:
    profile = _profile()

    restored_private = ModelProfile.model_validate_json(
        profile.to_private_storage_json()
    )
    restored_public = type(profile.to_public()).model_validate_json(
        profile.to_public().model_dump_json()
    )

    assert restored_private == profile
    assert restored_private.api_key is not None
    assert restored_private.api_key.get_secret_value() == SPECIAL_API_KEY
    assert restored_public == profile.to_public()


@pytest.mark.parametrize("api_key", [None, ""])
def test_model_profile_allows_null_or_empty_api_key(api_key: str | None) -> None:
    profile = _profile(api_key=api_key)

    if api_key is None:
        assert profile.api_key is None
    else:
        assert profile.api_key is not None
        assert profile.api_key.get_secret_value() == ""


@pytest.mark.parametrize("field_name", ["profile_name", "model_name"])
@pytest.mark.parametrize("value", ["", "   "])
def test_model_profile_rejects_empty_or_whitespace_required_names(
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError) as error:
        _profile(**{field_name: value})

    assert error.value.errors()[0]["loc"] == (field_name,)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:8080/v1",
        "https://models.example.test/v1",
    ],
)
def test_model_profile_accepts_http_and_https_base_urls(base_url: str) -> None:
    assert str(_profile(base_url=base_url).base_url).startswith(("http://", "https://"))


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///tmp/model",
        "ftp://models.example.test/v1",
        "javascript:alert(1)",
    ],
)
def test_model_profile_rejects_non_http_base_url_schemes(base_url: str) -> None:
    with pytest.raises(ValidationError) as error:
        _profile(base_url=base_url)

    assert error.value.errors()[0]["loc"] == ("base_url",)


def test_model_profile_rejects_naive_timestamps_without_leaking_api_key() -> None:
    with pytest.raises(ValidationError, match="timezone-aware") as error:
        _profile(created_at=datetime(2026, 7, 23, 12, 0))

    assert SPECIAL_API_KEY not in str(error.value)
    assert SPECIAL_API_KEY not in repr(error.value)


@pytest.mark.parametrize(
    "invalid_api_key",
    [
        [INVALID_API_KEY_MARKER],
        {"unexpected": INVALID_API_KEY_MARKER},
    ],
)
def test_model_profile_hides_invalid_api_key_from_common_error_representations(
    invalid_api_key: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        _profile(api_key=invalid_api_key)

    assert INVALID_API_KEY_MARKER not in str(error.value)
    assert INVALID_API_KEY_MARKER not in repr(error.value)
    assert INVALID_API_KEY_MARKER in str(error.value.errors())
    assert INVALID_API_KEY_MARKER in error.value.json()


def test_model_profile_rejects_updated_timestamp_before_creation() -> None:
    with pytest.raises(ValidationError, match="updated_at must not be earlier"):
        _profile(updated_at=datetime(2026, 7, 23, 11, 59, tzinfo=UTC))


def test_provider_connection_status_computes_formal_analysis_when_connected() -> None:
    status = _status()

    assert status.formal_analysis_allowed is True
    assert status.model_dump()["formal_analysis_allowed"] is True
    assert json.loads(status.model_dump_json())["formal_analysis_allowed"] is True


def test_provider_connection_status_rejects_formal_analysis_constructor_input() -> None:
    with pytest.raises(ValidationError) as error:
        _status(formal_analysis_allowed=True)

    assert error.value.errors()[0]["loc"] == ("formal_analysis_allowed",)


@pytest.mark.parametrize(
    ("state", "message", "tested_at"),
    [
        (ProviderConnectionState.UNTESTED, ProviderConnectionMessage.UNTESTED, None),
        (ProviderConnectionState.TESTING, ProviderConnectionMessage.TESTING, None),
        (ProviderConnectionState.FAILED, ProviderConnectionMessage.FAILED, NOW),
        (ProviderConnectionState.DISABLED, ProviderConnectionMessage.DISABLED, None),
        (ProviderConnectionState.DISABLED, ProviderConnectionMessage.DISABLED, NOW),
    ],
)
def test_provider_connection_status_blocks_formal_analysis_when_not_connected(
    state: ProviderConnectionState,
    message: ProviderConnectionMessage,
    tested_at: datetime | None,
) -> None:
    status = _status(
        connection_state=state,
        tested_at=tested_at,
        user_message=message,
    )

    assert status.formal_analysis_allowed is False


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (ProviderConnectionState.CONNECTED, ProviderConnectionMessage.CONNECTED),
        (ProviderConnectionState.FAILED, ProviderConnectionMessage.FAILED),
    ],
)
def test_provider_connection_status_requires_test_time_for_completed_results(
    state: ProviderConnectionState,
    message: ProviderConnectionMessage,
) -> None:
    with pytest.raises(ValidationError, match="requires tested_at"):
        _status(connection_state=state, tested_at=None, user_message=message)


@pytest.mark.parametrize(
    ("state", "message"),
    [
        (ProviderConnectionState.UNTESTED, ProviderConnectionMessage.UNTESTED),
        (ProviderConnectionState.TESTING, ProviderConnectionMessage.TESTING),
    ],
)
def test_provider_connection_status_rejects_test_time_before_a_completed_result(
    state: ProviderConnectionState,
    message: ProviderConnectionMessage,
) -> None:
    with pytest.raises(ValidationError, match="cannot have tested_at"):
        _status(connection_state=state, tested_at=NOW, user_message=message)


def test_provider_connection_status_is_an_immutable_snapshot() -> None:
    status = _status()

    for field_name, value in (
        ("connection_state", ProviderConnectionState.FAILED),
        ("tested_at", None),
        ("user_message", ProviderConnectionMessage.FAILED),
        ("model_name", "other-model"),
        ("formal_analysis_allowed", False),
    ):
        with pytest.raises(ValidationError):
            setattr(status, field_name, value)


def test_provider_connection_status_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as error:
        _status(unexpected=True)

    assert error.value.errors()[0]["loc"] == ("unexpected",)


def test_provider_connection_status_round_trips_without_computed_output_input() -> None:
    status = _status()

    restored = ProviderConnectionStatus.model_validate_json(
        status.model_dump_json(exclude_computed_fields=True)
    )

    assert restored == status
    assert restored.formal_analysis_allowed is True


def test_provider_connection_status_rejects_mismatched_safe_message() -> None:
    with pytest.raises(ValidationError, match="user_message"):
        _status(
            connection_state=ProviderConnectionState.FAILED,
            tested_at=NOW,
            user_message=ProviderConnectionMessage.CONNECTED,
        )


def test_provider_connection_status_rejects_naive_test_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _status(
            tested_at=datetime(2026, 7, 23, 12, 0),
        )
