"""Secret-safe provider failure contracts shared by API and UI boundaries."""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, model_validator

from ai_poc_planner.domain.models import ContractModel
from ai_poc_planner.providers.base import ProviderError


class ProviderOperation(StrEnum):
    READINESS = "readiness"
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    REPORT = "report"


_USER_ACTIONS: dict[str, str] = {
    "provider_auth_required": "請補充 API key 後再測試。",
    "provider_auth_failed": "請確認 API key 與端點權限後再試。",
    "provider_parameter_unsupported": "請檢查模型能力設定中的參數相容性。",
    "provider_structured_output_unsupported": (
        "請改用支援的結構化輸出模式，或啟用 JSON Object fallback。"
    ),
    "provider_not_found": "請確認端點網址與模型名稱。",
    "provider_timeout": "請稍後重試，或檢查端點負載與 timeout 設定。",
    "provider_connection_failed": "請確認端點正在執行且網路連線可用。",
    "provider_rate_limited": "請稍後重試，或降低請求頻率。",
    "provider_unavailable": "請稍後重試，並確認服務目前可用。",
    "provider_http_error": "請檢查端點設定與請求能力後再試。",
    "provider_invalid_response": "請確認端點回傳 OpenAI-compatible chat completion。",
    "provider_output_truncated": "請提高輸出預算後再試。",
    "provider_output_invalid": "請重試；若持續失敗，請檢查結構化輸出能力。",
    "model_profile_auth_required": "請輸入 API key，或改用不需要認證的端點。",
    "model_profile_auth_forbidden": "此認證模式不允許保存 API key，請清除後再試。",
    "model_profile_reasoning_unsupported": "此端點不支援 reasoning effort，請清除該設定。",
    "model_profile_structured_output_invalid": "請至少啟用一種並選擇支援的結構化輸出模式。",
}

_RETRYABLE = {
    "provider_timeout",
    "provider_connection_failed",
    "provider_rate_limited",
    "provider_unavailable",
}


class SafeProviderFailure(ContractModel):
    """Immutable failure data safe to expose through public boundaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    operation: ProviderOperation
    retryable: bool
    user_action: str

    @model_validator(mode="after")
    def validate_safe_action(self) -> SafeProviderFailure:
        expected = _USER_ACTIONS.get(self.code)
        if expected is None:
            raise ValueError("unknown provider failure code")
        if self.user_action != expected:
            raise ValueError("provider failure action must use the fixed safe text")
        if self.retryable != (self.code in _RETRYABLE):
            raise ValueError("provider failure retry policy is fixed")
        return self

    @classmethod
    def from_code(cls, code: str, operation: ProviderOperation) -> SafeProviderFailure:
        if code not in _USER_ACTIONS:
            code = "provider_http_error"
        return cls(
            code=code,
            operation=operation,
            retryable=code in _RETRYABLE,
            user_action=_USER_ACTIONS[code],
        )


class ProviderOperationError(ProviderError):
    """A provider failure carrying only the stable safe contract."""

    def __init__(self, failure: SafeProviderFailure) -> None:
        self.failure = failure
        self.code = failure.code
        self.operation = failure.operation
        self.retryable = failure.retryable
        self.user_action = failure.user_action
        super().__init__(failure.code)


__all__ = ["ProviderOperation", "ProviderOperationError", "SafeProviderFailure"]
