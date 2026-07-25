"""Opt-in production API UAT for the immutable Phase 5.2 report."""

# ruff: noqa: E501

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.providers.test_gemini_analysis_integration import _app
from tests.providers.test_nvidia_analysis_integration import (
    run_nvidia_discovery_and_analysis,
)

pytestmark = pytest.mark.nvidia


def _enabled() -> None:
    if os.environ.get("AI_POC_PLANNER_NVIDIA_REPORT_TEST") != "1":
        pytest.skip("set AI_POC_PLANNER_NVIDIA_REPORT_TEST=1 to run report UAT")
    if not os.environ.get("NVIDIA_API_KEY"):
        pytest.skip("NVIDIA_API_KEY is required for report UAT")


def test_nvidia_completes_immutable_planning_report(tmp_path: Path) -> None:
    _enabled()
    database_path, profile_path, project_id, profile_id, analysis = (
        run_nvidia_discovery_and_analysis(tmp_path)
    )
    endpoint = f"/v1/projects/{project_id}/versions/1/report"

    with TestClient(_app(database_path, profile_path)) as client:
        tested = client.post(f"/v1/model-profiles/{profile_id}/test")
        assert tested.status_code == 200
        created = client.post(endpoint)
        assert created.status_code == 201, created.json().get("error", {}).get("code")
        report = created.json()
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1").json()["status"]
            == "complete"
        )
        narration = report["report"]
        assert len(narration) == 19  # schema_version plus eighteen narration fields
        assert "conclusion" not in narration
        assert "weighted_total" not in narration
        markdown = report["markdown"]
        headings = [
            "## Executive Summary",
            "## Relevant Reviewed Cases",
            "## Fact-Backed Scoring Appendix",
            "## Hard Gates",
        ]
        assert all(item in markdown for item in headings)
        assert markdown.index(headings[0]) < markdown.index(headings[1])
        assert markdown.index(headings[1]) < markdown.index(headings[2])
        assert analysis["conclusion"] in markdown
        assert analysis["recommended_option_key"] in markdown
        assert str(analysis["weighted_total"]) in markdown
        assert analysis["gate_disposition"] in markdown
        duplicate = client.post(endpoint)
        assert duplicate.status_code == 409
        assert client.get(endpoint).json() == report

    with TestClient(_app(database_path, profile_path)) as reloaded:
        assert reloaded.get(endpoint).json() == report
        assert (
            reloaded.get(f"/v1/projects/{project_id}/versions/1").json()["status"]
            == "complete"
        )
