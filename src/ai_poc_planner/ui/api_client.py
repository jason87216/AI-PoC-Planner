"""Small HTTP-only client used by the Streamlit presentation layer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

_DEFAULT_TIMEOUT_SECONDS = 10.0
_SAFE_NETWORK_MESSAGE = "無法連線至規劃 API，請確認服務是否已啟動。"
_SAFE_RESPONSE_MESSAGE = "規劃 API 回傳了無法顯示的回應。"


class UiApiError(RuntimeError):
    """A safe API failure suitable for direct display in the Streamlit UI."""

    def __init__(
        self,
        *,
        code: str,
        user_message: str,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.user_message = user_message
        self.correlation_id = correlation_id


class StreamlitApiClient:
    """Call only the persisted FastAPI planning endpoints; never retry writes."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def create_run(
        self,
        natural_language_request: str,
        clarification_answers: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/planning/runs",
            json={
                "natural_language_request": natural_language_request,
                "clarification_answers": dict(clarification_answers or {}),
            },
        )

    def submit_clarifications(
        self,
        run_id: str,
        clarification_answers: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/planning/runs/{run_id}/clarifications",
            json={"clarification_answers": dict(clarification_answers)},
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/planning/runs/{run_id}")

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise UiApiError(
                code="api_unavailable",
                user_message=_SAFE_NETWORK_MESSAGE,
            ) from error

        if response.is_error:
            raise _ui_error_from_response(response)
        return _response_payload(response)


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise UiApiError(
            code="invalid_api_response",
            user_message=_SAFE_RESPONSE_MESSAGE,
        ) from error
    if not isinstance(payload, dict):
        raise UiApiError(
            code="invalid_api_response",
            user_message=_SAFE_RESPONSE_MESSAGE,
        )
    return payload


def _ui_error_from_response(response: httpx.Response) -> UiApiError:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = error.get("code")
        message = error.get("message")
        correlation_id = error.get("correlation_id")
        if isinstance(code, str) and isinstance(message, str):
            return UiApiError(
                code=code,
                user_message=message,
                correlation_id=(
                    correlation_id if isinstance(correlation_id, str) else None
                ),
            )
    return UiApiError(
        code="api_request_failed",
        user_message="規劃 API 暫時無法完成此請求。",
    )
