from __future__ import annotations

from ai_poc_planner.ui.model_profile_form import (
    capability_help,
    capability_label,
    create_profile_authentication_error,
    profile_payload,
)


def _payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "profile_name": "",
        "base_url": "",
        "model_name": "",
        "api_key": "",
        "structured_output_mode": "json_object",
        "reasoning_effort": "",
        "authentication": "none",
        "token_parameter": "max_tokens",
        "reasoning_parameter": "unsupported",
        "supports_json_schema": False,
        "supports_json_object": True,
        "is_enabled": True,
        "include_required_fields": False,
    }
    values.update(overrides)
    return profile_payload(**values)


def test_create_none_profile_rejects_entered_key_without_clear_control() -> None:
    assert (
        create_profile_authentication_error("none", "entered-only-for-request")
        == "none 認證模式不允許保存 API key，請清空目前輸入後再建立。"
    )
    assert create_profile_authentication_error("none", "") is None


def test_update_none_without_clear_omits_api_key() -> None:
    payload = _payload(api_key="", clear_api_key=False)

    assert "api_key" not in payload
    assert payload["capabilities"] == {
        "authentication": "none",
        "token_parameter": "max_tokens",
        "reasoning_parameter": "unsupported",
        "json_schema": False,
        "json_object": True,
    }


def test_update_none_with_clear_sends_explicit_null_api_key() -> None:
    payload = _payload(clear_api_key=True)

    assert payload["api_key"] is None


def test_capability_labels_are_product_facing_and_keep_stable_values() -> None:
    assert capability_label("authentication", "bearer_required") == (
        "必須使用 Bearer 認證（bearer_required）"
    )
    assert capability_label("token_parameter", "max_completion_tokens") == (
        "max_completion_tokens（部分端點使用）"
    )
    assert capability_label("reasoning_parameter", "unsupported") == (
        "不傳送推理參數（unsupported）"
    )
    assert capability_label("structured_output", "json_schema") == (
        "JSON Schema（較嚴格的欄位結構）"
    )


def test_capability_help_explains_explicit_vendor_neutral_selection() -> None:
    assert "端點文件" in capability_help("authentication")
    assert "不要依品牌或模型名稱猜測" in capability_help("structured_output")


def test_create_form_has_one_preferred_mode_and_keeps_wire_values() -> None:
    source = open("app_pages/model_settings.py", encoding="utf-8").read()
    create_form = source.split("if profiles:", 1)[0]

    assert "structured_output_mode = st.selectbox" not in source
    assert create_form.count('"偏好的結構化輸出模式（選填）"') == 1
    assert '"首選結構化輸出模式"' not in create_form
    assert "structured_output_mode=preferred_mode" in source

    for mode in ("json_schema", "json_object"):
        payload = _payload(structured_output_mode=mode)
        assert payload["structured_output_mode"] == mode

    assert "api_key" not in _payload(api_key="")
    assert _payload(api_key="new-key")["api_key"] == "new-key"
    assert _payload(clear_api_key=True)["api_key"] is None
