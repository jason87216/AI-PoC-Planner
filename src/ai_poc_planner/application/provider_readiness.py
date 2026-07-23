"""Process-local real-provider readiness boundary; it never falls back to fake."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.providers.base import (
    ProviderConnectionMessage,
    ProviderConnectionState,
    ProviderError,
)
from ai_poc_planner.providers.profiles import ModelProfile, ProviderConnectionStatus


class ChatCompletionAdapter(Protocol):
    def complete(self, **kwargs: object) -> str: ...


class ProviderReadinessError(RuntimeError):
    """Stable safe error for API callers; no provider body or secret is retained."""

    def __init__(self, code: str) -> None:
        self.code = code
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

    def invalidate(self, profile_id: UUID) -> None:
        """Forget a completed test when its persisted profile changes or disappears."""

        self._statuses.pop(profile_id, None)

    def selected_status(self) -> ProviderConnectionStatus | None:
        selected = self._profiles.get_selected()
        return self.status_for(selected) if selected is not None else None

    def status_for(self, profile: ModelProfile) -> ProviderConnectionStatus:
        status = self._statuses.get(profile.id)
        if status is not None and status.model_name == profile.model_name:
            return status
        return self._status(profile, ProviderConnectionState.UNTESTED, None)

    def test(self, profile_id: UUID) -> ProviderConnectionStatus:
        profile = self._profiles.get(profile_id)
        if not profile.is_enabled:
            status = self._status(profile, ProviderConnectionState.DISABLED, None)
            self._statuses[profile.id] = status
            raise ProviderReadinessError("profile_disabled")
        self._statuses[profile.id] = self._status(
            profile, ProviderConnectionState.TESTING, None
        )
        try:
            content = self._adapter_factory(profile).complete(
                messages=[
                    {"role": "system", "content": "You are a connection test."},
                    {"role": "user", "content": "Reply with a short confirmation."},
                ],
                temperature=0,
                max_tokens=8,
            )
            if not isinstance(content, str) or not content.strip():
                raise ProviderError("empty provider response")
        except ProviderError:
            status = self._status(
                profile, ProviderConnectionState.FAILED, self._clock()
            )
            self._statuses[profile.id] = status
            return status
        except Exception:
            status = self._status(
                profile, ProviderConnectionState.FAILED, self._clock()
            )
            self._statuses[profile.id] = status
            return status
        status = self._status(profile, ProviderConnectionState.CONNECTED, self._clock())
        self._statuses[profile.id] = status
        return status

    def require_formal_analysis_ready(self) -> ProviderConnectionStatus:
        selected = self._profiles.get_selected()
        if selected is None or not selected.is_enabled:
            raise ProviderReadinessError("provider_not_ready")
        status = self.status_for(selected)
        if not status.formal_analysis_allowed:
            raise ProviderReadinessError("provider_not_ready")
        return status

    @staticmethod
    def _status(
        profile: ModelProfile,
        state: ProviderConnectionState,
        tested_at: datetime | None,
    ) -> ProviderConnectionStatus:
        return ProviderConnectionStatus(
            profile_id=profile.id,
            connection_state=state,
            tested_at=tested_at,
            user_message=ProviderConnectionMessage[state.name],
            model_name=profile.model_name,
        )
