"""Process-local real-provider readiness boundary; it never falls back to fake."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from ai_poc_planner.domain.models import ContractModel
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.base import (
    ProviderConnectionMessage,
    ProviderConnectionState,
    ProviderError,
)
from ai_poc_planner.providers.errors import (
    ProviderOperation,
    ProviderOperationError,
    SafeProviderFailure,
)
from ai_poc_planner.providers.profiles import ModelProfile, ProviderConnectionStatus
from ai_poc_planner.providers.structured_output import StructuredOutputExecutor


class ChatCompletionAdapter(Protocol):
    def complete(self, **kwargs: object) -> str: ...


class ConnectionProbe(ContractModel):
    """Minimal provider-facing readiness contract."""

    status: Literal["ok"]


class ProviderReadinessError(RuntimeError):
    """Stable safe error for API callers; no provider body or secret is retained."""

    def __init__(self, code: str, failure: SafeProviderFailure | None = None) -> None:
        self.code = code
        self.failure = failure
        super().__init__(code)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ProviderReadinessService:
    """Test real profiles and retain only current-process safe status snapshots."""

    def __init__(
        self,
        *,
        profiles: LocalModelProfileRepository,
        adapter_factory: Callable[[ModelProfile], ChatCompletionAdapter],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._profiles = profiles
        self._adapter_factory = adapter_factory
        self._clock = clock
        self._statuses: dict[UUID, ProviderConnectionStatus] = {}
        self._fingerprints: dict[UUID, tuple[object, ...]] = {}

    def invalidate(self, profile_id: UUID) -> None:
        """Forget a completed test when its persisted profile changes or disappears."""

        self._statuses.pop(profile_id, None)
        self._fingerprints.pop(profile_id, None)

    def selected_status(self) -> ProviderConnectionStatus | None:
        selected = self._profiles.get_selected()
        return self.status_for(selected) if selected is not None else None

    def status_for(self, profile: ModelProfile) -> ProviderConnectionStatus:
        status = self._statuses.get(profile.id)
        if (
            status is not None
            and status.model_name == profile.model_name
            and self._fingerprints.get(profile.id) == self._profile_fingerprint(profile)
        ):
            return status
        return self._status(profile, ProviderConnectionState.UNTESTED, None)

    def test(self, profile_id: UUID) -> ProviderConnectionStatus:
        profile = self._profiles.get(profile_id)
        if not profile.is_enabled:
            status = self._status(profile, ProviderConnectionState.DISABLED, None)
            self._remember(profile, status)
            raise ProviderReadinessError("profile_disabled")
        self._remember(
            profile, self._status(profile, ProviderConnectionState.TESTING, None)
        )
        try:
            execution = StructuredOutputExecutor().execute(
                adapter=self._adapter_factory(profile),
                capabilities=profile.effective_capabilities,
                preferred_mode=profile.effective_structured_output_mode,
                operation=ProviderOperation.READINESS,
                schema_name="connection_probe",
                provider_contract=ConnectionProbe,
                messages=[
                    {"role": "system", "content": "You are a connection test."},
                    {
                        "role": "user",
                        "content": "Reply with the readiness JSON object.",
                    },
                ],
                temperature=0,
                logical_max_tokens=256,
                reasoning_effort=profile.reasoning_effort,
            )
        except ProviderOperationError as error:
            status = self._status(
                profile,
                ProviderConnectionState.FAILED,
                self._clock(),
                failure=error.failure,
            )
            self._remember(profile, status)
            return status
        except ProviderError as error:
            status = self._status(
                profile,
                ProviderConnectionState.FAILED,
                self._clock(),
                failure=SafeProviderFailure.from_code(
                    getattr(error, "code", "provider_http_error"),
                    ProviderOperation.READINESS,
                ),
            )
            self._remember(profile, status)
            return status
        except Exception:
            status = self._status(
                profile,
                ProviderConnectionState.FAILED,
                self._clock(),
                failure=SafeProviderFailure.from_code(
                    "provider_http_error", ProviderOperation.READINESS
                ),
            )
            self._remember(profile, status)
            return status
        status = self._status(
            profile,
            ProviderConnectionState.CONNECTED,
            self._clock(),
            mode_used=execution.mode_used,
            fallback_used=execution.fallback_used,
        )
        self._remember(profile, status)
        return status

    def require_formal_analysis_ready(self) -> ProviderConnectionStatus:
        selected = self._profiles.get_selected()
        if selected is None or not selected.is_enabled:
            raise ProviderReadinessError("provider_not_ready")
        return self.require_profile_ready(selected.id)

    def require_profile_ready(self, profile_id: UUID) -> ProviderConnectionStatus:
        profile = self._profiles.get(profile_id)
        if not profile.is_enabled:
            raise ProviderReadinessError("provider_not_ready")
        status = self.status_for(profile)
        if not status.formal_analysis_allowed:
            raise ProviderReadinessError(
                (
                    status.failure.code
                    if status.failure is not None
                    else "provider_not_ready"
                ),
                status.failure,
            )
        return status

    @staticmethod
    def _status(
        profile: ModelProfile,
        state: ProviderConnectionState,
        tested_at: datetime | None,
        *,
        failure: SafeProviderFailure | None = None,
        mode_used=None,
        fallback_used: bool = False,
    ) -> ProviderConnectionStatus:
        return ProviderConnectionStatus(
            profile_id=profile.id,
            connection_state=state,
            tested_at=tested_at,
            user_message=ProviderConnectionMessage[state.name],
            model_name=profile.model_name,
            failure=failure,
            mode_used=mode_used,
            fallback_used=fallback_used,
        )

    def _remember(
        self, profile: ModelProfile, status: ProviderConnectionStatus
    ) -> None:
        self._statuses[profile.id] = status
        self._fingerprints[profile.id] = self._profile_fingerprint(profile)

    @staticmethod
    def _profile_fingerprint(profile: ModelProfile) -> tuple[object, ...]:
        return (
            profile.model_name,
            profile.structured_output_mode,
            profile.reasoning_effort,
            profile.effective_capabilities.model_dump_json(),
            profile.api_key is not None,
            profile.is_enabled,
        )
