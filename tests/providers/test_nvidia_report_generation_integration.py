"""Opt-in report-only NVIDIA UAT using a production-valid assessed fixture."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.domain.enums import ProjectStatus
from ai_poc_planner.domain.project_history import SelectedModelSnapshot
from ai_poc_planner.persistence.analysis import SQLiteAnalysisRepository
from ai_poc_planner.persistence.connection import database_connection
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository
from ai_poc_planner.persistence.project_history import SQLiteProjectHistoryRepository
from ai_poc_planner.persistence.schema import initialize_database
from ai_poc_planner.providers.openai_compatible import OpenAICompatibleChatAdapter
from ai_poc_planner.providers.profiles import ModelProfile
from tests.support.assessed_snapshot import build_assessed_snapshot

pytestmark = pytest.mark.nvidia


def _enabled() -> None:
    if os.environ.get("AI_POC_PLANNER_NVIDIA_REPORT_TEST") != "1" or not os.environ.get(
        "NVIDIA_API_KEY"
    ):
        pytest.skip("set AI_POC_PLANNER_NVIDIA_REPORT_TEST=1 and NVIDIA_API_KEY")


class NvidiaCallRecorder:
    """Track only schema names while delegating every request to real NVIDIA."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._client = httpx.Client()

    def adapter_for(self, profile: ModelProfile) -> RecordingNvidiaAdapter:
        return RecordingNvidiaAdapter(profile, self)

    def close(self) -> None:
        self._client.close()


class RecordingNvidiaAdapter:
    def __init__(self, profile: ModelProfile, recorder: NvidiaCallRecorder) -> None:
        self._profile = profile
        self._recorder = recorder

    def complete(self, **kwargs: object) -> str:
        response_format = kwargs.get("response_format")
        name = getattr(response_format, "name", "json_object")
        self._recorder.calls.append(name)
        return OpenAICompatibleChatAdapter(
            base_url=str(self._profile.base_url),
            model_name=self._profile.model_name,
            api_key=(
                self._profile.api_key.get_secret_value()
                if self._profile.api_key is not None
                else None
            ),
            client=self._recorder._client,
            timeout_seconds=240 if name.startswith("report_") else 10,
            reasoning_effort=self._profile.reasoning_effort,
        ).complete(**kwargs)


def _app(database_path: Path, profile_path: Path, recorder: NvidiaCallRecorder):
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        connection_adapter_factory=recorder.adapter_for,
        analysis_adapter_factory=recorder.adapter_for,
    )


def _run_report_only_nvidia_uat(state_path: Path) -> None:
    database_path = state_path / "report.sqlite3"
    profile_path = state_path / "profiles.json"
    recorder = NvidiaCallRecorder()

    try:
        with TestClient(_app(database_path, profile_path, recorder)) as client:
            profile = client.post(
                "/v1/model-profiles",
                json={
                    "profile_name": "NVIDIA",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                    "model_name": "openai/gpt-oss-20b",
                    "api_key": os.environ["NVIDIA_API_KEY"],
                    "structured_output_mode": "json_schema",
                    "reasoning_effort": "low",
                },
            ).json()
            assert (
                client.post(f"/v1/model-profiles/{profile['id']}/select").status_code
                == 200
            )
            assert (
                client.post(f"/v1/model-profiles/{profile['id']}/test").status_code
                == 200
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

            # Safe assertion directly before the guard; no sensitive data is inspected.
            reloaded = database_connection(database_path)
            try:
                history = SQLiteProjectHistoryRepository(reloaded)
                assert (
                    history.get_version(fixture.project_id, 1).status
                    is ProjectStatus.ASSESSED
                )
                assert (
                    SQLiteAnalysisRepository(reloaded).get_by_version(
                        fixture.version_id
                    )
                    == fixture.expected_analysis
                )
            finally:
                reloaded.close()

            endpoint = f"/v1/projects/{fixture.project_id}/versions/1/report"
            created = client.post(endpoint)
            assert created.status_code == 201, {
                "code": created.json().get("error", {}).get("code"),
                "provider_calls": recorder.calls,
            }
            report = created.json()
            # These fields come from distinct NVIDIA calls: Part A and Part B.
            assert report["report"]["executive_summary"]
            assert report["report"]["open_issues_and_next_actions"]
            assert len(report["report"]) == 19
            assert recorder.calls[0] == "connection_probe"
            assert "report_part_a" in recorder.calls
            assert "report_part_b" in recorder.calls
            assert (
                client.get(f"/v1/projects/{fixture.project_id}/versions/1").json()[
                    "status"
                ]
                == "complete"
            )
            assert client.post(endpoint).status_code == 409
            assert client.get(endpoint).json() == report

        with TestClient(_app(database_path, profile_path, recorder)) as client:
            assert client.get(endpoint).json() == report
            assert (
                client.get(f"/v1/projects/{fixture.project_id}/versions/1").json()[
                    "status"
                ]
                == "complete"
            )
    finally:
        recorder.close()


def test_nvidia_generates_report_from_two_fresh_assessed_snapshots(
    tmp_path: Path,
) -> None:
    _enabled()
    for attempt in range(1, 3):
        state_path = tmp_path / f"fresh-report-state-{attempt}"
        state_path.mkdir()
        _run_report_only_nvidia_uat(state_path)
