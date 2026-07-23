"""Framework-neutral model-profile and provider-status contracts."""

from __future__ import annotations

import json
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    ConfigDict,
    Field,
    SecretStr,
    computed_field,
    model_validator,
)

from ai_poc_planner.domain.models import ContractModel, NonEmptyStr, UtcDateTime
from ai_poc_planner.providers.base import (
    ProviderConnectionMessage,
    ProviderConnectionState,
)


class ModelProfilePublic(ContractModel):
    """Safe model-profile data suitable for public API or UI responses."""

    schema_version: Literal["1.0"] = "1.0"
    id: UUID = Field(description="Stable internal model-profile identifier.")
    profile_name: NonEmptyStr
    base_url: AnyHttpUrl
    model_name: NonEmptyStr
    is_selected: bool
    is_enabled: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @model_validator(mode="after")
    def updated_at_is_not_earlier(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class ModelProfile(ModelProfilePublic):
    """Private profile contract; only private storage boundaries may reveal its key.

    ``hide_input_in_errors`` protects ordinary exception rendering, but raw
    ``ValidationError.errors()`` and ``ValidationError.json()`` may retain input.
    Those raw values are internal-only and must never be used for public responses,
    logs, or provider-status messages. A future API layer must convert errors to a
    safe contract without raw input.
    """

    model_config = ConfigDict(
        extra="forbid",
        hide_input_in_errors=True,
        use_enum_values=False,
    )

    api_key: SecretStr | None = Field(default=None, repr=False)

    def to_public(self) -> ModelProfilePublic:
        """Return the explicit public contract without an API key field."""

        return ModelProfilePublic.model_validate(
            self.model_dump(mode="json", exclude={"api_key"})
        )

    def to_private_storage_json(self) -> str:
        """Serialize plaintext API-key data for the future P1.2 private repository.

        This is the only deliberate plaintext API-key export. It must never be used
        for public APIs, logs, errors, or UI output.
        """

        payload = self.model_dump(mode="json")
        payload["api_key"] = (
            self.api_key.get_secret_value() if self.api_key is not None else None
        )
        return json.dumps(payload, separators=(",", ":"))


class ProviderConnectionStatus(ContractModel):
    """Immutable provider-status snapshot safe for public response use.

    ``tested_at`` is the time that produced the current completed connection-test
    result. It is absent while untested or testing, required for connected and
    failed, and optional for disabled so a disabled profile can retain its most
    recent completed test time. This contract guarantees only internal consistency;
    the trusted P1.4 connection-test service is responsible for creating a
    trustworthy ``connected`` snapshot.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    schema_version: Literal["1.0"] = "1.0"
    profile_id: UUID
    connection_state: ProviderConnectionState
    tested_at: UtcDateTime | None
    user_message: ProviderConnectionMessage
    model_name: NonEmptyStr

    @computed_field
    @property
    def formal_analysis_allowed(self) -> bool:
        """Whether this internally consistent snapshot permits formal analysis."""

        return (
            self.connection_state is ProviderConnectionState.CONNECTED
            and self.tested_at is not None
        )

    @model_validator(mode="after")
    def validate_connection_state(self) -> Self:
        expected_message = ProviderConnectionMessage[self.connection_state.name]
        if self.user_message is not expected_message:
            raise ValueError("user_message must match connection_state")
        if self.connection_state is ProviderConnectionState.CONNECTED:
            if self.tested_at is None:
                raise ValueError("connected status requires tested_at")
            return self
        if (
            self.connection_state is ProviderConnectionState.FAILED
            and self.tested_at is None
        ):
            raise ValueError("failed status requires tested_at")
        if (
            self.connection_state
            in {
                ProviderConnectionState.UNTESTED,
                ProviderConnectionState.TESTING,
            }
            and self.tested_at is not None
        ):
            raise ValueError("untested or testing status cannot have tested_at")
        return self
