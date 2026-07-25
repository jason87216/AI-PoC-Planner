"""Opt-in Gemini validation of the production Phase 3 → Phase 4 API flow."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository

pytestmark = pytest.mark.gemini

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_MODEL_NAME = "gemini-3.6-flash"


def _api_key() -> str:
    if os.environ.get("AI_POC_PLANNER_GEMINI_TEST") != "1":
        pytest.skip("set AI_POC_PLANNER_GEMINI_TEST=1 to run Gemini analysis UAT")
    if "GEMINI_API_KEY" not in os.environ:
        pytest.skip("GEMINI_API_KEY is required for Gemini analysis UAT")
    return os.environ["GEMINI_API_KEY"]


def _app(database_path: Path, profile_path: Path):
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter(())),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
    )


def _current_facts(client: TestClient, project_id: str) -> dict[str, dict[str, object]]:
    response = client.get(f"/v1/projects/{project_id}/versions/1/facts")
    assert response.status_code == 200
    return {item["fact_key"].strip().casefold(): item for item in response.json()}


def _answer_round(
    client: TestClient,
    project_id: str,
    questions: list[dict[str, object]],
    round_number: int,
) -> dict[str, object]:
    facts = _current_facts(client, project_id)
    answers: list[dict[str, object]] = []
    for index, question in enumerate(questions):
        existing = facts.get(str(question["fact_key"]).strip().casefold())
        if existing is not None and existing["status"] == "confirmed":
            answers.append(
                {
                    "question_id": question["id"],
                    "answer_status": "answered",
                    "answer": existing["value"],
                }
            )
        elif existing is not None:
            answers.append(
                {
                    "question_id": question["id"],
                    "answer_status": existing["status"],
                    "answer": None,
                }
            )
        else:
            answers.append(
                {
                    "question_id": question["id"],
                    "answer_status": "answered" if index == 0 else "unknown",
                    "answer": "The supervisor will review the suggestion."
                    if index == 0
                    else None,
                }
            )

    payload: dict[str, object] = {"answers": answers}
    if round_number == 1:
        staff_fact = facts["users_and_owners"]
        payload["additional_facts"] = [
            {
                "fact_key": "peak_volume",
                "status": "confirmed",
                "value": "Peak periods have about 80 to 120 requests per day.",
            },
            {
                "fact_key": "integration_availability",
                "status": "unknown",
                "value": None,
            },
        ]
        payload["corrections"] = [
            {
                "target_fact_id": staff_fact["id"],
                "status": "confirmed",
                "value": "Four customer-service staff and one supervisor.",
                "correction_reason": "The staffing count was corrected by the user.",
            }
        ]
    submitted = client.post(
        f"/v1/projects/{project_id}/versions/1/interview-answers", json=payload
    )
    assert submitted.status_code == 200
    return submitted.json()


def test_gemini_completes_discovery_and_evidence_backed_analysis(
    tmp_path: Path,
) -> None:
    api_key = _api_key()
    database_path = tmp_path / "gemini-phase-four-uat.sqlite3"
    profile_path = tmp_path / "gemini-phase-four-profiles.json"
    project_id: str
    result: dict[str, object]

    with TestClient(_app(database_path, profile_path)) as client:
        profile = client.post(
            "/v1/model-profiles",
            json={
                "profile_name": "Gemini Phase 4 integration",
                "base_url": _BASE_URL,
                "model_name": _MODEL_NAME,
                "api_key": api_key,
            },
        )
        assert profile.status_code == 201
        public_profile = profile.json()
        assert "api_key" not in public_profile
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
                    "四名客服人员和一名主管人工阅读后复制到试算表，再依问题类别分派。"
                    "大部分分派规则可以用明确类别与渠道判断，但特殊案件仍需人工理解。"
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
                    "所有 AI 建议必须由客服人员确认，AI 不得自动回复客户，"
                    "也不得执行最终分派或处理决定。"
                ),
            },
        )
        assert created.status_code == 201
        body = created.json()
        project_id = body["project"]["id"]
        assert body["version"]["status"] == "draft"
        assert (
            body["version"]["selected_model"]["profile_name"]
            == "Gemini Phase 4 integration"
        )

        first = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
        assert first.status_code == 200
        assert first.json()["understanding_revision"] == 1
        available_data = _current_facts(client, project_id)["available_data"]
        corrected = client.post(
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
        assert corrected.status_code == 200
        assert corrected.json()["status"] == "correction_pending"
        regenerated = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
        assert regenerated.status_code == 200
        assert regenerated.json()["understanding_revision"] == 2
        confirmed = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/confirm"
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "ready_for_interview"

        round_sizes: list[int] = []
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
            round_sizes.append(len(questions))
            state = _answer_round(client, project_id, questions, round_number)
            if state["status"] == "ready_for_assessment":
                break

        session = client.get(f"/v1/projects/{project_id}/versions/1/discovery")
        version = client.get(f"/v1/projects/{project_id}/versions/1")
        assert session.status_code == 200
        assert version.status_code == 200
        assert session.json()["status"] == "ready_for_assessment"
        assert version.json()["status"] == "ready_for_assessment"
        assert len(round_sizes) <= 3 and all(size <= 3 for size in round_sizes)

        analysis = client.post(f"/v1/projects/{project_id}/versions/1/analysis")
        assert analysis.status_code == 201
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
        assert {score["dimension"] for score in result["scores"]} == {
            "business_value",
            "data_readiness",
            "technical_fit",
            "architecture_controllability",
            "governance_readiness",
            "user_adoption",
        }
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
        loaded = reloaded.get(f"/v1/projects/{project_id}/versions/1/analysis")
        assert loaded.status_code == 200
        assert loaded.json() == result
        assert (
            reloaded.get(f"/v1/projects/{project_id}/versions/1/discovery").json()[
                "status"
            ]
            == "ready_for_assessment"
        )
        assert (
            reloaded.get("/v1/provider-status").json()["connection_state"] == "untested"
        )

    with sqlite3.connect(database_path) as connection:
        dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
    for forbidden in ("system prompt", "chain of thought", "authorization"):
        assert forbidden not in dump
