"""Offline API coverage for the report-only assessed-snapshot flow."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.planning_report import REPORT_SECTION_KEYS
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database
from tests.support.assessed_snapshot import build_assessed_snapshot


class ReportAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs["response_format"]
        name = response_format.name
        self.calls.append(name)
        if name == "connection_probe":
            return "connected"
        sections = (
            REPORT_SECTION_KEYS[:9]
            if name == "report_part_a"
            else REPORT_SECTION_KEYS[9:]
        )
        return json.dumps(
            {
                key: {"content": "Evidence-backed PoC guidance.", "fact_refs": ["F001"]}
                for key in sections
            }
        )


def _app(database_path: Path, profile_path: Path, adapter: ReportAdapter):
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=lambda _: adapter,
        analysis_adapter_factory=lambda _: adapter,
    )


def test_report_only_flow_commits_assessed_snapshot_and_completes_version(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "report.sqlite3"
    profile_path = tmp_path / "profiles.json"
    adapter = ReportAdapter()

    with TestClient(_app(database_path, profile_path, adapter)) as client:
        profile = client.post(
            "/v1/model-profiles",
            json={
                "profile_name": "Offline report test",
                "base_url": "http://127.0.0.1:8080/v1",
                "model_name": "offline-model",
                "api_key": "safe-test-marker",
            },
        ).json()
        assert (
            client.post(f"/v1/model-profiles/{profile['id']}/select").status_code == 200
        )
        assert (
            client.post(f"/v1/model-profiles/{profile['id']}/test").status_code == 200
        )

        connection = database_connection(database_path)
        try:
            initialize_database(connection)
            fixture = build_assessed_snapshot(
                connection,
                SelectedModelSnapshot(
                    profile_id=profile["id"],
                    profile_name=profile["profile_name"],
                    model_name=profile["model_name"],
                ),
            )
        finally:
            connection.close()

        # Safe diagnostic assertion before the POST guard; no prompt or provider data.
        reloaded = database_connection(database_path)
        try:
            history = SQLiteProjectHistoryRepository(reloaded)
            assert (
                history.get_version(fixture.project_id, 1).status
                is ProjectStatus.ASSESSED
            )
            assert (
                SQLiteAnalysisRepository(reloaded).get_by_version(fixture.version_id)
                == fixture.expected_analysis
            )
        finally:
            reloaded.close()

        endpoint = f"/v1/projects/{fixture.project_id}/versions/1/report"
        created = client.post(endpoint)
        assert created.status_code == 201, created.json()
        report = created.json()
        assert (
            client.get(f"/v1/projects/{fixture.project_id}/versions/1").json()["status"]
            == "complete"
        )
        assert adapter.calls == ["connection_probe", "report_part_a", "report_part_b"]
        assert client.post(endpoint).status_code == 409
        assert client.get(endpoint).json() == report

    with TestClient(_app(database_path, profile_path, ReportAdapter())) as client:
        assert client.get(endpoint).json() == report
