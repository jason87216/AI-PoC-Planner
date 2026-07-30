import pytest

from ai_poc_planner.config import (
    PROVIDER_READINESS_TIMEOUT_ENV,
    Settings,
    provider_readiness_timeout_seconds,
)


def test_settings_load_without_dotenv_or_api_key() -> None:
    settings = Settings.from_env({})

    assert settings.fake_model is True
    assert settings.model_api_key is None
    assert settings.app_env == "development"


def test_settings_names_match_environment_contract() -> None:
    settings = Settings.from_env(
        {
            "APP_ENV": "test",
            "LOG_LEVEL": "DEBUG",
            "FAKE_MODEL": "false",
            "MODEL_PROVIDER": "compatible-provider",
            "MODEL_NAME": "test-model",
            "MODEL_BASE_URL": "https://example.invalid/v1",
            "MODEL_API_KEY": "test-only-value",
            "EMBEDDING_PROVIDER": "compatible-provider",
            "EMBEDDING_MODEL": "test-embedding-model",
            "EMBEDDING_BASE_URL": "https://example.invalid/v1",
            "EMBEDDING_API_KEY": "test-only-value",
            "DATABASE_URL": "sqlite:///./data/test.db",
            "FAISS_INDEX_PATH": "./data/test-faiss",
            "LANGSMITH_TRACING": "false",
            "LANGSMITH_API_KEY": "",
            "LANGSMITH_PROJECT": "test-project",
        }
    )

    assert settings.app_env == "test"
    assert settings.fake_model is False
    assert settings.model_name == "test-model"
    assert settings.langsmith_tracing is False


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, 60.0),
        ("1", 1.0),
        ("60", 60.0),
        ("300", 300.0),
        ("1.5", 1.5),
    ],
)
def test_provider_readiness_timeout_accepts_safe_values(
    raw_value: str | None, expected: float
) -> None:
    environ = {} if raw_value is None else {PROVIDER_READINESS_TIMEOUT_ENV: raw_value}

    assert provider_readiness_timeout_seconds(environ) == expected


@pytest.mark.parametrize(
    "raw_value",
    ["", "0", "-1", "301", "not-a-number", "NaN", "Infinity", "-Infinity"],
)
def test_provider_readiness_timeout_rejects_invalid_values(raw_value: str) -> None:
    with pytest.raises(ValueError, match="provider_readiness_timeout_invalid") as error:
        provider_readiness_timeout_seconds({PROVIDER_READINESS_TIMEOUT_ENV: raw_value})

    assert getattr(error.value, "code", None) == "provider_readiness_timeout_invalid"
    if raw_value:
        assert raw_value not in str(error.value)
