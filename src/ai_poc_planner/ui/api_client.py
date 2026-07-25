"""Safe, thin client for the local FastAPI product boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class ApiClientError(RuntimeError):
    """A public API failure represented by a safe, user-facing message."""

    def __init__(self, code: str, user_message: str) -> None:
        self.code = code
        self.user_message = user_message
        super().__init__(user_message)


_USER_MESSAGES = {
    "provider_not_ready": "尚未有可用的已測試模型設定。",
    "model_profile_not_found": "找不到指定的模型設定。",
    "project_not_found": "找不到指定的專案。",
    "internal_error": "服務暫時無法完成此操作，請稍後再試。",
}


class ApiClient:
    """Call product endpoints without importing application or persistence code."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url or "http://127.0.0.1:8000",
            timeout=httpx.Timeout(10.0),
            follow_redirects=False,
        )

    def list_projects(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v1/projects")
        return self._list_of_objects(payload)

    def provider_status(self) -> dict[str, Any]:
        return self._object(self._request("GET", "/v1/provider-status"))

    def list_profiles(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v1/model-profiles")
        return self._list_of_objects(payload)

    def create_profile(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._object(self._request("POST", "/v1/model-profiles", payload))

    def update_profile(
        self, profile_id: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        return self._object(
            self._request("PATCH", f"/v1/model-profiles/{profile_id}", payload)
        )

    def delete_profile(self, profile_id: str) -> None:
        self._request("DELETE", f"/v1/model-profiles/{profile_id}", expected={204})

    def select_profile(self, profile_id: str) -> dict[str, Any]:
        return self._object(
            self._request("POST", f"/v1/model-profiles/{profile_id}/select")
        )

    def test_profile(self, profile_id: str) -> dict[str, Any]:
        return self._object(
            self._request("POST", f"/v1/model-profiles/{profile_id}/test")
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        expected: set[int] | None = None,
    ) -> object:
        expected = expected or {200, 201}
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as error:
            raise ApiClientError(
                "api_unavailable", "目前無法連線到本機服務，請稍後再試。"
            ) from error
        if response.status_code not in expected:
            raise self._error_from_response(response)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as error:
            raise ApiClientError(
                "invalid_response", "服務回應格式無法使用，請稍後再試。"
            ) from error

    @staticmethod
    def _object(payload: object) -> dict[str, Any]:
        if isinstance(payload, dict) and all(isinstance(key, str) for key in payload):
            return payload
        raise ApiClientError("invalid_response", "服務回應格式無法使用，請稍後再試。")

    @staticmethod
    def _list_of_objects(payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list) and all(
            isinstance(item, dict) for item in payload
        ):
            return payload
        raise ApiClientError("invalid_response", "服務回應格式無法使用，請稍後再試。")

    @staticmethod
    def _error_from_response(response: httpx.Response) -> ApiClientError:
        code = "internal_error"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict) and isinstance(error.get("code"), str):
                    code = error["code"]
        except ValueError:
            pass
        return ApiClientError(
            code, _USER_MESSAGES.get(code, _USER_MESSAGES["internal_error"])
        )
