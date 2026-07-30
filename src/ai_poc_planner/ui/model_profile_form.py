"""Pure model-profile form validation and request-payload helpers."""

from __future__ import annotations

from typing import Any


def create_profile_authentication_error(
    authentication: str, api_key: str
) -> str | None:
    if authentication == "none" and api_key:
        return "none 認證模式不允許保存 API key，請清空目前輸入後再建立。"
    return None


def profile_payload(
    *,
    profile_name: str,
    base_url: str,
    model_name: str,
    api_key: str,
    structured_output_mode: str,
    reasoning_effort: str,
    authentication: str,
    token_parameter: str,
    reasoning_parameter: str,
    supports_json_schema: bool,
    supports_json_object: bool,
    clear_api_key: bool = False,
    is_enabled: bool,
    include_required_fields: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"is_enabled": is_enabled}
    if include_required_fields or profile_name:
        payload["profile_name"] = profile_name
    if include_required_fields or base_url:
        payload["base_url"] = base_url
    if include_required_fields or model_name:
        payload["model_name"] = model_name
    if clear_api_key:
        payload["api_key"] = None
    elif api_key:
        payload["api_key"] = api_key
    if structured_output_mode:
        payload["structured_output_mode"] = structured_output_mode
    if reasoning_parameter == "unsupported":
        payload["reasoning_effort"] = None
    elif reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if include_required_fields or any(
        [
            authentication,
            token_parameter,
            reasoning_parameter,
            supports_json_schema,
            supports_json_object,
        ]
    ):
        payload["capabilities"] = {
            "authentication": authentication,
            "token_parameter": token_parameter,
            "reasoning_parameter": reasoning_parameter,
            "json_schema": supports_json_schema,
            "json_object": supports_json_object,
        }
    return payload
