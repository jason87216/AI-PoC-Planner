"""Pure model-profile form validation and request-payload helpers."""

from __future__ import annotations

from typing import Any

_CAPABILITY_LABELS = {
    "authentication": {
        "none": "不需要認證（none）",
        "bearer_optional": "可選 Bearer 認證（bearer_optional）",
        "bearer_required": "必須使用 Bearer 認證（bearer_required）",
    },
    "token_parameter": {
        "max_tokens": "max_tokens（一般輸出上限）",
        "max_completion_tokens": "max_completion_tokens（部分端點使用）",
    },
    "reasoning_parameter": {
        "unsupported": "不傳送推理參數（unsupported）",
        "reasoning_effort": "傳送 reasoning_effort（reasoning_effort）",
    },
    "structured_output": {
        "json_schema": "JSON Schema（較嚴格的欄位結構）",
        "json_object": "JSON Object（物件格式）",
    },
}

_CAPABILITY_HELP = {
    "authentication": "請依端點文件選擇；端點需要認證時，目前只支援 Bearer 認證。",
    "token_parameter": "選擇端點接受的輸出預算欄位；不會同時送出兩個欄位。",
    "reasoning_parameter": "若端點不支援推理參數，請選擇不傳送並留白推理強度。",
    "structured_output": (
        "至少選擇一種端點支援的結構化輸出模式；不要依品牌或模型名稱猜測能力。"
    ),
    "preferred_mode": "這是首選模式；必須包含在上方已勾選的支援模式中。",
}


def capability_label(kind: str, value: str) -> str:
    """Return a reader-friendly label while preserving the wire value."""

    return _CAPABILITY_LABELS.get(kind, {}).get(value, value)


def capability_help(kind: str) -> str:
    """Return bounded product guidance for one capability control."""

    return _CAPABILITY_HELP.get(kind, "請依端點文件確認後再保存設定。")


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
