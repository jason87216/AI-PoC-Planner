"""Environment-backed settings with a safe local fake-model default."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

PROVIDER_READINESS_TIMEOUT_ENV = "AI_POC_PLANNER_PROVIDER_READINESS_TIMEOUT_SECONDS"
DEFAULT_PROVIDER_READINESS_TIMEOUT_SECONDS = 60.0
MIN_PROVIDER_READINESS_TIMEOUT_SECONDS = 1.0
MAX_PROVIDER_READINESS_TIMEOUT_SECONDS = 300.0


class ProviderReadinessTimeoutConfigurationError(ValueError):
    """Safe, stable error for an invalid process-level readiness timeout."""

    code = "provider_readiness_timeout_invalid"

    def __init__(self) -> None:
        super().__init__(self.code)


def provider_readiness_timeout_seconds(
    environ: Mapping[str, str] = os.environ,
) -> float:
    """Return the validated process-level timeout for provider readiness."""

    raw_value = environ.get(PROVIDER_READINESS_TIMEOUT_ENV)
    if raw_value is None:
        return DEFAULT_PROVIDER_READINESS_TIMEOUT_SECONDS
    try:
        value = float(raw_value.strip())
    except (AttributeError, TypeError, ValueError) as error:
        raise ProviderReadinessTimeoutConfigurationError from error
    if not isfinite(value) or not (
        MIN_PROVIDER_READINESS_TIMEOUT_SECONDS
        <= value
        <= MAX_PROVIDER_READINESS_TIMEOUT_SECONDS
    ):
        raise ProviderReadinessTimeoutConfigurationError
    return value


def _optional_value(environ: Mapping[str, str], name: str) -> str | None:
    value = environ.get(name, "").strip()
    return value or None


def _boolean_value(environ: Mapping[str, str], name: str, *, default: bool) -> bool:
    value = environ.get(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True, slots=True)
class Settings:
    """Minimal configuration contract for local and future provider modes."""

    app_env: str = "development"
    log_level: str = "INFO"
    fake_model: bool = True
    model_provider: str = "openai"
    model_name: str | None = None
    model_base_url: str | None = None
    model_api_key: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str | None = None
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    database_url: str = "sqlite:///./data/planner.db"
    faiss_index_path: str = "./data/faiss"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "ai-poc-planner-local"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Load settings without requiring dotenv or any secret."""

        values = os.environ if environ is None else environ
        return cls(
            app_env=values.get("APP_ENV", "development"),
            log_level=values.get("LOG_LEVEL", "INFO"),
            fake_model=_boolean_value(values, "FAKE_MODEL", default=True),
            model_provider=values.get("MODEL_PROVIDER", "openai"),
            model_name=_optional_value(values, "MODEL_NAME"),
            model_base_url=_optional_value(values, "MODEL_BASE_URL"),
            model_api_key=_optional_value(values, "MODEL_API_KEY"),
            embedding_provider=values.get("EMBEDDING_PROVIDER", "openai"),
            embedding_model=_optional_value(values, "EMBEDDING_MODEL"),
            embedding_base_url=_optional_value(values, "EMBEDDING_BASE_URL"),
            embedding_api_key=_optional_value(values, "EMBEDDING_API_KEY"),
            database_url=values.get("DATABASE_URL", "sqlite:///./data/planner.db"),
            faiss_index_path=values.get("FAISS_INDEX_PATH", "./data/faiss"),
            langsmith_tracing=_boolean_value(
                values, "LANGSMITH_TRACING", default=False
            ),
            langsmith_api_key=_optional_value(values, "LANGSMITH_API_KEY"),
            langsmith_project=values.get("LANGSMITH_PROJECT", "ai-poc-planner-local"),
        )
