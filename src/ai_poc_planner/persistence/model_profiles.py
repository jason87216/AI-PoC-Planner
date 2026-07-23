"""Private local JSON persistence for single-user model profiles."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

from pydantic import ValidationError

from ai_poc_planner.providers.profiles import ModelProfile

_SCHEMA_VERSION = "1.0"
_UNSET = object()


class ModelProfileRepositoryError(RuntimeError):
    """Stable, secret-safe base error for local model-profile persistence."""

    code = "model_profile_repository_error"


class ModelProfileNotFoundError(ModelProfileRepositoryError):
    code = "model_profile_not_found"


class DuplicateModelProfileNameError(ModelProfileRepositoryError):
    code = "duplicate_model_profile_name"


class SelectedModelProfileDisabledError(ModelProfileRepositoryError):
    code = "selected_model_profile_disabled"


class InvalidStoredModelProfilesError(ModelProfileRepositoryError):
    code = "invalid_stored_model_profiles"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalized_api_key(value: str | None) -> str | None:
    return value if value is not None and value != "" else None


class LocalModelProfileRepository:
    """Persist profiles privately with atomic replacement and a process-local lock.

    API keys are deliberately stored as plaintext in the user's local data file for
    this MVP. This class is a private boundary and must never be used to produce an
    API response, log payload, or UI representation.
    """

    def __init__(
        self,
        *,
        path: str | Path | None = None,
        uuid_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._path = Path(path) if path is not None else self.default_path()
        self._uuid_factory = uuid_factory
        self._clock = clock
        self._lock = RLock()

    @property
    def path(self) -> Path:
        """Return the private file path for composition and tests, not public output."""

        return self._path

    @staticmethod
    def default_path() -> Path:
        override = os.environ.get("AI_POC_PLANNER_DATA_DIR")
        if override:
            return Path(override) / "model_profiles.json"
        if os.name == "nt":
            local_app_data = os.environ.get("LOCALAPPDATA")
            root = (
                Path(local_app_data)
                if local_app_data
                else Path.home() / "AppData" / "Local"
            )
            return root / "AI-PoC-Planner" / "model_profiles.json"
        return (
            Path.home() / ".local" / "share" / "ai-poc-planner" / "model_profiles.json"
        )

    def list(self) -> list[ModelProfile]:
        with self._lock:
            return self._load()

    def get(self, profile_id: UUID) -> ModelProfile:
        with self._lock:
            return self._find(self._load(), profile_id)

    def get_selected(self) -> ModelProfile | None:
        with self._lock:
            return next(
                (profile for profile in self._load() if profile.is_selected), None
            )

    def create(
        self,
        *,
        profile_name: str,
        base_url: str,
        model_name: str,
        api_key: str | None = None,
        is_enabled: bool = True,
    ) -> ModelProfile:
        with self._lock:
            profiles = self._load()
            timestamp = self._clock()
            try:
                profile = ModelProfile(
                    id=self._uuid_factory(),
                    profile_name=profile_name,
                    base_url=base_url,
                    model_name=model_name,
                    api_key=_normalized_api_key(api_key),
                    is_selected=False,
                    is_enabled=is_enabled,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            except ValidationError as error:
                raise ModelProfileRepositoryError(
                    "model profile input is invalid"
                ) from error
            self._ensure_unique(profiles, profile)
            self._write([*profiles, profile])
            return profile

    def update(
        self,
        profile_id: UUID,
        *,
        profile_name: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None | object = _UNSET,
        is_enabled: bool | None = None,
    ) -> ModelProfile:
        with self._lock:
            profiles = self._load()
            current = self._find(profiles, profile_id)
            key_value = (
                current.api_key.get_secret_value()
                if api_key is _UNSET and current.api_key is not None
                else _normalized_api_key(api_key if isinstance(api_key, str) else None)
            )
            try:
                updated = ModelProfile(
                    id=current.id,
                    profile_name=(
                        current.profile_name if profile_name is None else profile_name
                    ),
                    base_url=current.base_url if base_url is None else base_url,
                    model_name=current.model_name if model_name is None else model_name,
                    api_key=key_value,
                    is_selected=(
                        current.is_selected if is_enabled is not False else False
                    ),
                    is_enabled=current.is_enabled if is_enabled is None else is_enabled,
                    created_at=current.created_at,
                    updated_at=self._clock(),
                )
            except ValidationError as error:
                raise ModelProfileRepositoryError(
                    "model profile input is invalid"
                ) from error
            self._ensure_unique(profiles, updated, exclude_id=current.id)
            replacement = [
                updated if item.id == current.id else item for item in profiles
            ]
            self._write(replacement)
            return updated

    def delete(self, profile_id: UUID) -> None:
        with self._lock:
            profiles = self._load()
            self._find(profiles, profile_id)
            self._write([profile for profile in profiles if profile.id != profile_id])

    def select(self, profile_id: UUID) -> ModelProfile:
        with self._lock:
            profiles = self._load()
            selected = self._find(profiles, profile_id)
            if not selected.is_enabled:
                raise SelectedModelProfileDisabledError(
                    "disabled model profile cannot be selected"
                )
            timestamp = self._clock()
            updated_profiles = [
                self._replace_selected(profile, profile.id == selected.id, timestamp)
                for profile in profiles
            ]
            self._write(updated_profiles)
            return self._find(updated_profiles, selected.id)

    @staticmethod
    def _replace_selected(
        profile: ModelProfile,
        is_selected: bool,
        timestamp: datetime,
    ) -> ModelProfile:
        return ModelProfile.model_validate(
            {
                **profile.model_dump(mode="json", exclude={"api_key"}),
                "api_key": (
                    profile.api_key.get_secret_value()
                    if profile.api_key is not None
                    else None
                ),
                "is_selected": is_selected,
                "updated_at": timestamp,
            }
        )

    @staticmethod
    def _find(profiles: list[ModelProfile], profile_id: UUID) -> ModelProfile:
        if not isinstance(profile_id, UUID):
            raise ModelProfileNotFoundError("model profile was not found")
        for profile in profiles:
            if profile.id == profile_id:
                return profile
        raise ModelProfileNotFoundError("model profile was not found")

    @staticmethod
    def _ensure_unique(
        profiles: list[ModelProfile],
        candidate: ModelProfile,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        normalized_name = candidate.profile_name.casefold()
        if any(
            profile.id != exclude_id
            and profile.profile_name.casefold() == normalized_name
            for profile in profiles
        ):
            raise DuplicateModelProfileNameError("model profile name already exists")

    def _load(self) -> list[ModelProfile]:
        if not self._path.exists():
            return []
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            if (
                not isinstance(payload, dict)
                or payload.get("schema_version") != _SCHEMA_VERSION
                or not isinstance(payload.get("profiles"), list)
            ):
                raise ValueError("unsupported profile storage schema")
            profiles = [
                ModelProfile.model_validate(item) for item in payload["profiles"]
            ]
            self._validate_profiles(profiles)
            return profiles
        except (
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as error:
            raise InvalidStoredModelProfilesError(
                "stored model profiles are invalid"
            ) from error

    @staticmethod
    def _validate_profiles(profiles: list[ModelProfile]) -> None:
        ids = [profile.id for profile in profiles]
        names = [profile.profile_name.casefold() for profile in profiles]
        selected = [profile for profile in profiles if profile.is_selected]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate model profile ID")
        if len(names) != len(set(names)):
            raise ValueError("duplicate model profile name")
        if len(selected) > 1 or any(not profile.is_enabled for profile in selected):
            raise ValueError("invalid selected model profile")

    def _write(self, profiles: list[ModelProfile]) -> None:
        self._validate_profiles(profiles)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "profiles": [
                json.loads(profile.to_private_storage_json()) for profile in profiles
            ],
        }
        temporary_path: Path | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".model_profiles-",
                suffix=".tmp",
                dir=self._path.parent,
                text=True,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            if os.name != "nt":
                try:
                    os.chmod(temporary_path, 0o600)
                except OSError:
                    pass
            os.replace(temporary_path, self._path)
        except OSError as error:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ModelProfileRepositoryError(
                "model profiles could not be saved"
            ) from error
