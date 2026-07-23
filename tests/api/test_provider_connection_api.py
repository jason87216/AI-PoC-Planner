from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleProviderError

SECRET_MARKER = "api-secret-marker-9b6f3a20"
RAW_MARKER = "provider-raw-marker-7d14"


class SuccessfulAdapter:
    def complete(self, **_: object) -> str:
        return "connection ok"


class FailingAdapter:
    def complete(self, **_: object) -> str:
        raise OpenAICompatibleProviderError("provider_unavailable")


def _client(tmp_path: Path, adapter: object = SuccessfulAdapter()) -> TestClient:
    repository = LocalModelProfileRepository(path=tmp_path / "model_profiles.json")
    return TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            model_profile_repository=repository,
            connection_adapter_factory=lambda _: adapter,
        )
    )


def _create_profile(client: TestClient, *, name: str = "Local") -> dict[str, object]:
    response = client.post(
        "/v1/model-profiles",
        json={
            "profile_name": name,
            "base_url": "http://localhost:8080/v1",
            "model_name": "qwen-local",
            "api_key": SECRET_MARKER,
        },
    )
    assert response.status_code == 201
    assert SECRET_MARKER not in response.text
    return response.json()


def test_profile_crud_returns_only_public_contract_and_safe_validation(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    profile = _create_profile(client)

    listed = client.get("/v1/model-profiles")
    invalid = client.post(
        "/v1/model-profiles",
        json={
            "profile_name": "Bad",
            "base_url": "http://localhost:8080/v1",
            "model_name": "qwen-local",
            "api_key": [SECRET_MARKER],
        },
    )
    deleted = client.delete(f"/v1/model-profiles/{profile['id']}")

    assert listed.status_code == 200
    assert listed.json() == [profile]
    assert "api_key" not in profile
    assert invalid.status_code == 422
    assert SECRET_MARKER not in invalid.text
    assert deleted.status_code == 204


def test_selected_status_connection_test_and_readiness_guard(tmp_path: Path) -> None:
    client = _client(tmp_path)
    profile = _create_profile(client)

    assert client.post(f"/v1/model-profiles/{profile['id']}/select").status_code == 200
    assert client.get("/v1/provider-status").json()["connection_state"] == "untested"
    tested = client.post(f"/v1/model-profiles/{profile['id']}/test")
    ready = client.get("/v1/provider-readiness")

    assert tested.status_code == 200
    assert tested.json()["connection_state"] == "connected"
    assert tested.json()["formal_analysis_allowed"] is True
    assert ready.status_code == 200


def test_edit_disable_and_delete_invalidate_process_status(tmp_path: Path) -> None:
    client = _client(tmp_path)
    profile = _create_profile(client)
    client.post(f"/v1/model-profiles/{profile['id']}/select")
    client.post(f"/v1/model-profiles/{profile['id']}/test")

    edited = client.patch(
        f"/v1/model-profiles/{profile['id']}", json={"model_name": "updated"}
    )
    not_ready = client.get("/v1/provider-readiness")
    disabled = client.patch(
        f"/v1/model-profiles/{profile['id']}", json={"is_enabled": False}
    )
    deleted = client.delete(f"/v1/model-profiles/{profile['id']}")

    assert edited.status_code == 200
    assert not_ready.status_code == 409
    assert not_ready.json()["error"]["code"] == "provider_not_ready"
    assert disabled.json()["is_selected"] is False
    assert deleted.status_code == 204


def test_failed_connection_keeps_safe_failed_status_without_raw_response(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, FailingAdapter())
    profile = _create_profile(client)
    client.post(f"/v1/model-profiles/{profile['id']}/select")

    response = client.post(f"/v1/model-profiles/{profile['id']}/test")

    assert response.status_code == 200
    assert response.json()["connection_state"] == "failed"
    assert RAW_MARKER not in response.text


def test_disabled_profile_cannot_be_selected_or_tested_and_new_registry_is_untested(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    profile = _create_profile(client)
    client.patch(f"/v1/model-profiles/{profile['id']}", json={"is_enabled": False})

    selected = client.post(f"/v1/model-profiles/{profile['id']}/select")
    tested = client.post(f"/v1/model-profiles/{profile['id']}/test")

    assert selected.status_code == 409
    assert tested.status_code == 409

    restarted = _client(tmp_path)
    restarted.patch(f"/v1/model-profiles/{profile['id']}", json={"is_enabled": True})
    restarted.post(f"/v1/model-profiles/{profile['id']}/select")
    assert restarted.get("/v1/provider-status").json()["connection_state"] == "untested"
