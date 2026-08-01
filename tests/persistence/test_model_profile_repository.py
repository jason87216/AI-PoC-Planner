from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from ai_poc_planner.persistence.model_profiles import (
    DuplicateModelProfileNameError,
    InvalidStoredModelProfilesError,
    LocalModelProfileRepository,
    ModelProfileNotFoundError,
    ModelProfileRepositoryError,
    SelectedModelProfileDisabledError,
)
from ai_poc_planner.providers import (
    AuthenticationMode,
    OpenAICompatibleCapabilities,
    ReasoningParameter,
    StructuredOutputMode,
    TokenParameter,
)

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
SECRET_MARKER = "repository-secret-marker-2e7c4d91"


def _repository(tmp_path: Path) -> LocalModelProfileRepository:
    return LocalModelProfileRepository(
        path=tmp_path / "model_profiles.json",
        uuid_factory=uuid4,
        clock=lambda: NOW,
    )


def test_empty_repository_and_default_path_stay_outside_project_root(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)

    assert repository.list() == []
    assert repository.path.parent == tmp_path
    assert "AI PoC Planner" not in str(LocalModelProfileRepository.default_path())


def test_create_list_get_update_delete_and_private_key_round_trip(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)

    created = repository.create(
        profile_name=" Local llama.cpp ",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
        api_key=SECRET_MARKER,
    )
    restored = LocalModelProfileRepository(path=repository.path).get(created.id)
    assert repository.list() == [created]
    updated = repository.update(created.id, model_name="qwen-updated")

    assert created.profile_name == "Local llama.cpp"
    assert restored.api_key is not None
    assert restored.api_key.get_secret_value() == SECRET_MARKER
    assert updated.model_name == "qwen-updated"
    assert updated.created_at == NOW
    assert updated.updated_at >= NOW
    repository.delete(created.id)
    with pytest.raises(ModelProfileNotFoundError):
        repository.get(created.id)


def test_legacy_profile_json_without_capabilities_loads_with_safe_defaults(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    profile = repository.create(
        profile_name="Legacy",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
    )
    payload = json.loads(repository.path.read_text(encoding="utf-8"))
    payload["profiles"][0].pop("capabilities", None)
    repository.path.write_text(json.dumps(payload), encoding="utf-8")

    restored = repository.get(profile.id)

    assert (
        restored.effective_capabilities.authentication
        is AuthenticationMode.BEARER_OPTIONAL
    )
    assert restored.effective_capabilities.token_parameter is TokenParameter.MAX_TOKENS
    assert restored.effective_capabilities.json_schema is False
    assert restored.effective_capabilities.json_object is True


def test_explicit_capabilities_round_trip_and_omitted_update_preserves_them(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    capabilities = OpenAICompatibleCapabilities(
        authentication=AuthenticationMode.BEARER_REQUIRED,
        token_parameter=TokenParameter.MAX_COMPLETION_TOKENS,
        reasoning_parameter=ReasoningParameter.REASONING_EFFORT,
        json_schema=True,
        json_object=True,
    )
    profile = repository.create(
        profile_name="Cloud",
        base_url="https://provider.example/v1",
        model_name="cloud-model",
        api_key=SECRET_MARKER,
        structured_output_mode=StructuredOutputMode.JSON_SCHEMA,
        reasoning_effort="low",
        capabilities=capabilities,
    )

    restored = LocalModelProfileRepository(path=repository.path).get(profile.id)
    preserved = repository.update(profile.id, model_name="cloud-model-v2")

    assert restored.capabilities == capabilities
    assert (
        restored.effective_capabilities.token_parameter
        is TokenParameter.MAX_COMPLETION_TOKENS
    )
    assert preserved.capabilities == capabilities


def test_capabilities_can_be_cleared_to_legacy_inference(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    profile = repository.create(
        profile_name="Explicit",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
        structured_output_mode=StructuredOutputMode.JSON_OBJECT,
        capabilities=OpenAICompatibleCapabilities(
            authentication=AuthenticationMode.NONE,
            token_parameter=TokenParameter.MAX_TOKENS,
            reasoning_parameter=ReasoningParameter.UNSUPPORTED,
            json_schema=False,
            json_object=True,
        ),
    )

    restored = repository.update(profile.id, capabilities=None)

    assert restored.capabilities is None
    assert (
        restored.effective_capabilities.authentication
        is AuthenticationMode.BEARER_OPTIONAL
    )


def test_none_authentication_clears_key_only_when_explicitly_requested(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    profile = repository.create(
        profile_name="Local",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
        api_key=SECRET_MARKER,
    )
    none_capabilities = OpenAICompatibleCapabilities(
        authentication=AuthenticationMode.NONE,
        token_parameter=TokenParameter.MAX_TOKENS,
        reasoning_parameter=ReasoningParameter.UNSUPPORTED,
        json_schema=False,
        json_object=True,
    )

    with pytest.raises(
        ModelProfileRepositoryError, match="model_profile_auth_forbidden"
    ):
        repository.update(profile.id, capabilities=none_capabilities)

    cleared = repository.update(
        profile.id,
        api_key=None,
        capabilities=none_capabilities,
    )

    assert cleared.api_key is None
    assert cleared.effective_capabilities.authentication is AuthenticationMode.NONE


def test_repository_keeps_replaces_and_clears_api_key_without_leaking_it(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    profile = repository.create(
        profile_name="Local",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
        api_key=SECRET_MARKER,
    )

    preserved = repository.update(profile.id, model_name="new-model")
    cleared = repository.update(profile.id, api_key="")
    replaced = repository.update(profile.id, api_key="replacement-key")

    assert preserved.api_key is not None
    assert preserved.api_key.get_secret_value() == SECRET_MARKER
    assert cleared.api_key is None
    assert replaced.api_key is not None
    assert SECRET_MARKER not in repr(repository.list())
    assert SECRET_MARKER not in repository.get(profile.id).model_dump_json()


def test_duplicate_names_are_trimmed_and_case_insensitive(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.create(
        profile_name="Local llama.cpp",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
    )

    with pytest.raises(DuplicateModelProfileNameError):
        repository.create(
            profile_name="  local LLAMA.CPP  ",
            base_url="http://localhost:8081/v1",
            model_name="qwen-other",
        )


def test_selecting_profile_keeps_exactly_one_enabled_selection(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    first = repository.create(
        profile_name="First",
        base_url="http://localhost:8080/v1",
        model_name="first",
    )
    second = repository.create(
        profile_name="Second",
        base_url="http://localhost:8081/v1",
        model_name="second",
    )

    selected = repository.select(second.id)

    assert selected.is_selected is True
    assert repository.get(first.id).is_selected is False
    assert repository.get_selected() == selected


def test_disabled_profile_cannot_be_selected_and_disabling_selected_clears_it(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    profile = repository.create(
        profile_name="Local",
        base_url="http://localhost:8080/v1",
        model_name="qwen-local",
    )
    repository.select(profile.id)

    disabled = repository.update(profile.id, is_enabled=False)

    assert disabled.is_selected is False
    assert repository.get_selected() is None
    with pytest.raises(SelectedModelProfileDisabledError):
        repository.select(profile.id)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        json.dumps({"schema_version": "2.0", "profiles": []}),
        json.dumps({"schema_version": "1.0", "profiles": [{"bad": "profile"}]}),
        json.dumps({"schema_version": "1.0", "profiles": []}),
    ],
)
def test_invalid_or_unsupported_storage_is_rejected_without_silent_repair(
    tmp_path: Path,
    payload: str,
) -> None:
    repository = _repository(tmp_path)
    repository.path.write_text(payload, encoding="utf-8")

    if payload == json.dumps({"schema_version": "1.0", "profiles": []}):
        assert repository.list() == []
    else:
        with pytest.raises(InvalidStoredModelProfilesError):
            repository.list()


def test_atomic_write_failure_is_a_stable_repository_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)

    def fail_replace(_: Path, __: Path) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(
        "ai_poc_planner.persistence.model_profiles.os.replace", fail_replace
    )

    with pytest.raises(
        ModelProfileRepositoryError, match="model profiles could not"
    ) as error:
        repository.create(
            profile_name="Local",
            base_url="http://localhost:8080/v1",
            model_name="qwen-local",
            api_key=SECRET_MARKER,
        )

    assert SECRET_MARKER not in str(error.value)
    assert SECRET_MARKER not in repr(error.value)
