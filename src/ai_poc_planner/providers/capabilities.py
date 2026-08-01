"""Explicit capabilities for the shared OpenAI-compatible transport."""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, model_validator

from ai_poc_planner.domain.models import ContractModel


class AuthenticationMode(StrEnum):
    """How the endpoint expects bearer authentication."""

    NONE = "none"
    BEARER_OPTIONAL = "bearer_optional"
    BEARER_REQUIRED = "bearer_required"


class TokenParameter(StrEnum):
    """Logical output-budget field accepted by the endpoint."""

    MAX_TOKENS = "max_tokens"
    MAX_COMPLETION_TOKENS = "max_completion_tokens"


class ReasoningParameter(StrEnum):
    """Optional reasoning request parameter supported by the endpoint."""

    UNSUPPORTED = "unsupported"
    REASONING_EFFORT = "reasoning_effort"


class OpenAICompatibleCapabilities(ContractModel):
    """Immutable, vendor-neutral transport capabilities for one endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    authentication: AuthenticationMode = AuthenticationMode.BEARER_OPTIONAL
    token_parameter: TokenParameter = TokenParameter.MAX_TOKENS
    reasoning_parameter: ReasoningParameter = ReasoningParameter.UNSUPPORTED
    json_schema: bool = False
    json_object: bool = True

    @model_validator(mode="after")
    def requires_structured_output_mode(self) -> OpenAICompatibleCapabilities:
        if not self.json_schema and not self.json_object:
            raise ValueError("model_profile_structured_output_invalid")
        return self
