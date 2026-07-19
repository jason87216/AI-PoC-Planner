from ai_poc_planner.config import Settings


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
