"""Opt-in NVIDIA NIM validation of the production Phase 3 → Phase 4 API flow."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.providers.test_gemini_analysis_integration import (
    _answer_round,
    _app,
    _current_facts,
)

pytestmark = pytest.mark.nvidia

_BASE_URL = "https://integrate.api.nvidia.com/v1"
_MODEL_NAME = "openai/gpt-oss-20b"


def _api_key() -> str:
    if os.environ.get("AI_POC_PLANNER_NVIDIA_TEST") != "1":
        pytest.skip("set AI_POC_PLANNER_NVIDIA_TEST=1 to run NVIDIA analysis UAT")
    if "NVIDIA_API_KEY" not in os.environ:
        pytest.skip("NVIDIA_API_KEY is required for NVIDIA analysis UAT")
    return os.environ["NVIDIA_API_KEY"]


def test_nvidia_completes_discovery_and_evidence_backed_analysis(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nvidia-phase-four-uat.sqlite3"
    profile_path = tmp_path / "nvidia-phase-four-profiles.json"
    project_id: str
    result: dict[str, object]

    with TestClient(_app(database_path, profile_path)) as client:
        profile = client.post(
            "/v1/model-profiles",
            json={
                "profile_name": "NVIDIA GPT-OSS 20B UAT",
                "base_url": _BASE_URL,
                "model_name": _MODEL_NAME,
                "structured_output_mode": "json_schema",
                "reasoning_effort": "low",
                "api_key": _api_key(),
                "is_enabled": True,
            },
        )
        assert profile.status_code == 201
        public_profile = profile.json()
        assert "api_key" not in public_profile
        assert public_profile["structured_output_mode"] == "json_schema"
        assert public_profile["reasoning_effort"] == "low"
        assert (
            client.post(f"/v1/model-profiles/{public_profile['id']}/select").status_code
            == 200
        )
        tested = client.post(f"/v1/model-profiles/{public_profile['id']}/test")
        assert tested.status_code == 200
        assert tested.json()["connection_state"] == "connected"
        assert tested.json()["formal_analysis_allowed"] is True

        created = client.post(
            "/v1/discovery-projects",
            json={
                "project_name": "客服请求分流 PoC",
                "current_workflow_problem": (
                    "客户问题通过 Email 与 LINE 进入。"
                    "四名客服人员和一名主管人工阅读后复制到试算表，"
                    "再依问题类别分派。大部分分派规则可以用明确类别与渠道判断，"
                    "但特殊案件仍需人工理解。"
                ),
                "desired_outcome": (
                    "缩短分类与转派时间。AI 只能提供分类建议，不允许自动回复客户，"
                    "也不允许自动做最终分派或处理决定。"
                ),
                "available_data": (
                    "目前有三个月 Email 与 LINE 汇出资料，但分类标签不完整，"
                    "也尚未建立代表性的验证样本。"
                ),
                "users_and_owners": (
                    "四名客服人员与一名客服主管，主管负责最终流程与 PoC 验收。"
                ),
                "known_constraints": (
                    "目前资料已获内部 PoC 测试授权，可以传送至经核准的外部模型 API。"
                    "所有 AI 分类与转派建议必须由客服人员确认。"
                    "AI 不得自动回复客户，也不得执行最终分派或处理决定。"
                ),
            },
        )
        assert created.status_code == 201
        project_id = created.json()["project"]["id"]
        assert created.json()["version"]["selected_model"]["model_name"] == _MODEL_NAME

        first = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
        assert first.status_code == 200
        available_data = _current_facts(client, project_id)["available_data"]
        correction = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/corrections",
            json={
                "corrections": [
                    {
                        "target_fact_id": available_data["id"],
                        "status": "confirmed",
                        "value": (
                            "目前有两个月 Email 与 LINE 汇出资料，但分类标签不完整，"
                            "也尚未建立代表性的验证样本。"
                        ),
                        "correction_reason": "使用者修正资料期间。",
                    }
                ]
            },
        )
        assert correction.status_code == 200
        regenerated = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
        assert regenerated.status_code == 200
        assert regenerated.json()["understanding_revision"] == 2
        assert (
            client.post(
                f"/v1/projects/{project_id}/versions/1/understanding/confirm"
            ).status_code
            == 200
        )

        for round_number in range(1, 4):
            generated = client.post(
                f"/v1/projects/{project_id}/versions/1/interview-rounds"
            )
            assert generated.status_code == 200
            questions = generated.json()
            if not questions:
                break
            assert 1 <= len(questions) <= 3
            assert all(
                item["question"]
                and item["why_it_matters"]
                and item["affected_judgement"]
                and item["example"]
                for item in questions
            )
            state = _answer_round(client, project_id, questions, round_number)
            if state["status"] == "ready_for_assessment":
                break

        session = client.get(f"/v1/projects/{project_id}/versions/1/discovery")
        assert session.json()["status"] == "ready_for_assessment"
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1").json()["status"]
            == "ready_for_assessment"
        )

        analysis = client.post(f"/v1/projects/{project_id}/versions/1/analysis")
        assert analysis.status_code == 201, analysis.json().get("error", {}).get("code")
        result = analysis.json()
        assert 2 <= len(result["options"]) <= 4
        assert any(option["option_kind"] == "non_ai" for option in result["options"])
        recommended = next(
            option
            for option in result["options"]
            if option["option_key"] == result["recommended_option_key"]
        )
        compatible = {
            "suitable_for_ai": "ai",
            "better_suited_to_non_ai": "non_ai",
            "establish_non_ai_foundations_before_ai": "foundations_first",
            "hybrid_ai_and_non_ai": "hybrid",
        }
        assert recommended["option_kind"] == compatible[result["conclusion"]]
        assert len(result["scores"]) == 6
        assert all(1 <= score["rating"] <= 5 for score in result["scores"])
        assert all(score["evidence_fact_refs"] for score in result["scores"])
        assert result["weighted_total"] == sum(
            score["weighted_points"] for score in result["scores"]
        )
        assert result["gate_disposition"] in {
            "pass",
            "requires_controls",
            "assistive_only",
            "blocked",
        }
        assert (
            client.post(f"/v1/projects/{project_id}/versions/1/analysis").status_code
            == 409
        )
        assert (
            client.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
            == result
        )

    with TestClient(_app(database_path, profile_path)) as reloaded:
        assert (
            reloaded.get(f"/v1/projects/{project_id}/versions/1/analysis").json()
            == result
        )
        assert (
            reloaded.get("/v1/provider-status").json()["connection_state"] == "untested"
        )

    with sqlite3.connect(database_path) as connection:
        dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
        for forbidden in (
            "system prompt",
            "chain of thought",
            "reasoning_content",
            "authorization: bearer",
            "bearer ",
        ):
            assert forbidden not in dump
