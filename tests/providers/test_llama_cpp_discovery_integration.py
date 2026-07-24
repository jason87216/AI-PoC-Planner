"""Opt-in, real llama.cpp validation of the complete Phase 3 API flow."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository

pytestmark = pytest.mark.llama_cpp


def _environment() -> tuple[str, str, str | None]:
    if os.environ.get("AI_POC_PLANNER_LLAMA_CPP_DISCOVERY_TEST") != "1":
        pytest.skip("set AI_POC_PLANNER_LLAMA_CPP_DISCOVERY_TEST=1 to run discovery")
    base_url = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_BASE_URL")
    model_name = os.environ.get("AI_POC_PLANNER_LLAMA_CPP_MODEL")
    if not base_url or not model_name:
        pytest.skip("llama.cpp base URL and model environment variables are required")
    return base_url, model_name, os.environ.get("AI_POC_PLANNER_LLAMA_CPP_API_KEY")


def _app(database_path: Path, profile_path: Path):
    return create_app(
        chat_model=GenericFakeChatModel(messages=iter([])),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
    )


def test_user_started_llama_cpp_completes_phase_three_discovery(tmp_path: Path) -> None:
    base_url, model_name, api_key = _environment()
    database_path = tmp_path / "phase-three-uat.sqlite3"
    profile_path = tmp_path / "phase-three-profiles.json"
    project_id: str

    with TestClient(_app(database_path, profile_path)) as client:
        profile = client.post(
            "/v1/model-profiles",
            json={
                "profile_name": "llama.cpp discovery integration",
                "base_url": base_url,
                "model_name": model_name,
                "api_key": api_key or "",
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
        assert client.get("/v1/provider-readiness").status_code == 200

        created = client.post(
            "/v1/discovery-projects",
            json={
                "project_name": "客服请求分流 PoC",
                "current_workflow_problem": (
                    "客户问题通过 Email 与 LINE 进入，五名客服人工阅读后复制到试算表，"
                    "再决定交给谁处理。"
                ),
                "desired_outcome": (
                    "缩短分类与转派时间，但不允许 AI 自动回复客户或做最终处理决定。"
                ),
                "available_data": (
                    "目前有三个月 Email 与 LINE 汇出资料，但分类标签不完整。"
                ),
                "users_and_owners": "五名客服人员与一名客服主管。",
                "known_constraints": "资料只能在本机处理，所有建议必须由客服人员确认。",
            },
        )
        assert created.status_code == 201
        body = created.json()
        project_id = body["project"]["id"]
        assert body["version"]["version_number"] == 1
        assert body["session"]["status"] == "brief_submitted"
        assert body["version"]["selected_model"]["profile_name"] == (
            "llama.cpp discovery integration"
        )

        first_understanding = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding"
        )
        assert first_understanding.status_code == 200
        assert first_understanding.json()["understanding_revision"] == 1

        data_fact = next(
            item
            for item in client.get(f"/v1/projects/{project_id}/versions/1/facts").json()
            if item["fact_key"] == "available_data"
        )
        correction = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/corrections",
            json={
                "corrections": [
                    {
                        "target_fact_id": data_fact["id"],
                        "status": "confirmed",
                        "value": (
                            "目前有两个月 Email 与 LINE 汇出资料，但分类标签不完整。"
                        ),
                        "correction_reason": "资料期间已重新确认。",
                    }
                ]
            },
        )
        assert correction.status_code == 200
        assert correction.json()["status"] == "correction_pending"
        history = client.get(
            f"/v1/projects/{project_id}/versions/1/facts/history"
        ).json()
        assert sum(item["fact_key"] == "available_data" for item in history) == 2
        assert next(
            item
            for item in client.get(f"/v1/projects/{project_id}/versions/1/facts").json()
            if item["fact_key"] == "available_data"
        )["value"].startswith("目前有两个月")

        regenerated = client.post(f"/v1/projects/{project_id}/versions/1/understanding")
        assert regenerated.status_code == 200
        assert regenerated.json()["understanding_revision"] == 2
        confirmed = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/confirm"
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "ready_for_interview"
        repeated_confirmation = client.post(
            f"/v1/projects/{project_id}/versions/1/understanding/confirm"
        )
        assert repeated_confirmation.status_code == 409
        assert repeated_confirmation.json()["error"]["code"] == (
            "understanding_already_confirmed"
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
            current_facts = client.get(
                f"/v1/projects/{project_id}/versions/1/facts"
            ).json()
            by_key = {
                item["fact_key"].strip().casefold(): item for item in current_facts
            }
            answers = []
            for index, question in enumerate(questions):
                existing = by_key.get(question["fact_key"].strip().casefold())
                if existing and existing["status"] == "confirmed":
                    answers.append(
                        {
                            "question_id": question["id"],
                            "answer_status": "answered",
                            "answer": existing["value"],
                        }
                    )
                elif existing:
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
                            "answer": "about 100" if index == 0 else None,
                        }
                    )
            payload: dict[str, object] = {"answers": answers}
            if round_number == 1:
                staff_fact = next(
                    item
                    for item in client.get(
                        f"/v1/projects/{project_id}/versions/1/facts"
                    ).json()
                    if item["fact_key"] == "users_and_owners"
                )
                payload["additional_facts"] = [
                    {
                        "fact_key": "peak_volume",
                        "status": "confirmed",
                        "value": "高峰时段每日约有 80 至 120 件请求。",
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
                        "value": "四名客服人员与一名主管。",
                        "correction_reason": "人员编制已重新确认。",
                    }
                ]
            submitted = client.post(
                f"/v1/projects/{project_id}/versions/1/interview-answers",
                json=payload,
            )
            assert submitted.status_code == 200
            if submitted.json()["status"] == "ready_for_assessment":
                break

        session = client.get(f"/v1/projects/{project_id}/versions/1/discovery").json()
        version = client.get(f"/v1/projects/{project_id}/versions/1").json()
        assert session["status"] == "ready_for_assessment"
        assert version["status"] == "ready_for_assessment"
        assert session["current_round"] <= 3

    with TestClient(_app(database_path, profile_path)) as reloaded:
        assert (
            reloaded.get(f"/v1/projects/{project_id}/versions/1/discovery").json()[
                "status"
            ]
            == "ready_for_assessment"
        )
        assert reloaded.get(f"/v1/projects/{project_id}/versions/1/messages").json()
        facts = reloaded.get(f"/v1/projects/{project_id}/versions/1/facts").json()
        assert any(item["fact_key"] == "peak_volume" for item in facts)
        assert any(item["fact_key"] == "integration_availability" for item in facts)
        assert any(item["fact_key"] == "users_and_owners" for item in facts)
        assert (
            reloaded.get("/v1/provider-status").json()["connection_state"] == "untested"
        )

    with sqlite3.connect(database_path) as connection:
        dump = "\n".join(str(row) for row in connection.iterdump()).casefold()
    for forbidden in ("system prompt", "chain of thought", "authorization"):
        assert forbidden not in dump
