from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.errors import DatabasePreflightError
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.persistence.schema import initialize_database


def _app(database_path: Path):
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter([])),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(
            path=database_path.with_suffix(".json")
        ),
    )


def test_database_preflight_creates_schema_before_runtime_identity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "planner.sqlite3"

    with TestClient(_app(database_path)) as client:
        assert client.get("/v1/projects").status_code == 200

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def test_v7_database_is_migrated_before_runtime_identity(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(database_path)
    initialize_database(connection)
    connection.execute("PRAGMA user_version = 7")
    connection.commit()
    connection.close()

    with TestClient(_app(database_path)) as client:
        assert client.get("/v1/projects").json() == []

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9
    finally:
        connection.close()


def test_failed_database_preflight_prevents_ready_runtime(tmp_path: Path) -> None:
    database_path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 99")
    connection.commit()
    connection.close()

    with pytest.raises(DatabasePreflightError) as raised:
        with TestClient(_app(database_path)):
            pass

    assert str(database_path) not in str(raised.value)
    assert "SQL" not in str(raised.value)
