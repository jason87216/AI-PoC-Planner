from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository

SENSITIVE_MARKER = "not-a-real-secret-marker"


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            chat_model=GenericFakeChatModel(messages=iter([])),
            database_path=tmp_path / "phase-two.sqlite3",
            model_profile_repository=LocalModelProfileRepository(
                path=tmp_path / "model_profiles.json"
            ),
        )
    )


def _message(
    client: TestClient,
    project_id: str,
    version_number: int,
    *,
    role: str,
    message_kind: str,
    content: str,
) -> dict[str, object]:
    response = client.post(
        f"/v1/projects/{project_id}/versions/{version_number}/messages",
        json={"role": role, "message_kind": message_kind, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_phase_two_api_uat_preserves_visible_history_and_fact_revisions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "phase-two.sqlite3"
    client = _client(tmp_path)
    created = client.post("/v1/projects", json={"project_name": "客服流程改善評估"})

    assert created.status_code == 201
    version_one = created.json()
    project_id = version_one["project_id"]
    assert version_one["version_number"] == 1
    assert version_one["status"] == "draft"
    summary = client.get("/v1/projects")
    assert summary.status_code == 200
    assert summary.json()[0]["project_name"] == "客服流程改善評估"
    assert summary.json()[0]["version_number"] == 1

    user_input = _message(
        client,
        project_id,
        1,
        role="user",
        message_kind="user_input",
        content="客服需要更快回覆。",
    )
    understanding = _message(
        client,
        project_id,
        1,
        role="assistant",
        message_kind="ai_understanding",
        content="目前假設痛點是回覆速度。",
    )
    confirmation = _message(
        client,
        project_id,
        1,
        role="user",
        message_kind="confirmation",
        content="這個理解正確。",
    )
    _message(
        client,
        project_id,
        1,
        role="assistant",
        message_kind="question",
        content="哪個團隊負責？",
    )
    _message(
        client,
        project_id,
        1,
        role="user",
        message_kind="answer",
        content="客服營運團隊。",
    )

    assumed = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/assumptions",
        json={
            "fact_key": "流程負責人",
            "value": "客服營運",
            "reference_message_ids": [understanding["id"]],
        },
    )
    assert assumed.status_code == 201
    confirmed = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/{assumed.json()['id']}/confirm",
        json={"reference_message_ids": [confirmation["id"]]},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    ordinary_overwrite = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/assumptions",
        json={
            "fact_key": " 流程負責人 ",
            "value": "不同值",
            "reference_message_ids": [understanding["id"]],
        },
    )
    assert ordinary_overwrite.status_code == 409
    assert ordinary_overwrite.json()["error"]["code"] == "fact_correction_required"

    correction = _message(
        client,
        project_id,
        1,
        role="user",
        message_kind="correction",
        content="實際由服務營運負責。",
    )
    corrected = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/{confirmed.json()['id']}/correct",
        json={
            "status": "confirmed",
            "value": "服務營運",
            "correction_reason": "組織職責已確認",
            "reference_message_ids": [correction["id"]],
        },
    )
    assert corrected.status_code == 200
    current_facts = client.get(f"/v1/projects/{project_id}/versions/1/facts")
    history = client.get(f"/v1/projects/{project_id}/versions/1/facts/history")
    assert current_facts.json()[0]["value"] == "服務營運"
    assert len(history.json()) == 3

    unknown = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/unknown",
        json={
            "fact_key": "資料保留期間",
            "reference_message_ids": [user_input["id"]],
        },
    )
    missing = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/missing",
        json={
            "fact_key": "基準工時資料",
            "reference_message_ids": [user_input["id"]],
        },
    )
    assert unknown.status_code == missing.status_code == 201

    completed = client.post(f"/v1/projects/{project_id}/versions/1/complete")
    assert completed.status_code == 200
    blocked_message = client.post(
        f"/v1/projects/{project_id}/versions/1/messages",
        json={"role": "user", "message_kind": "answer", "content": "blocked"},
    )
    blocked_fact = client.post(
        f"/v1/projects/{project_id}/versions/1/facts/unknown",
        json={"fact_key": "blocked", "reference_message_ids": [user_input["id"]]},
    )
    assert blocked_message.status_code == blocked_fact.status_code == 409
    assert blocked_message.json()["error"]["code"] == "completed_version_immutable"

    next_version = client.post(f"/v1/projects/{project_id}/versions/1/next")
    assert next_version.status_code == 201
    assert next_version.json()["version_number"] == 2
    assert next_version.json()["based_on_version_id"] == version_one["id"]
    copied_messages = client.get(f"/v1/projects/{project_id}/versions/2/messages")
    copied_facts = client.get(f"/v1/projects/{project_id}/versions/2/facts")
    assert [message["sequence"] for message in copied_messages.json()] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert all(message["copied_from_message_id"] for message in copied_messages.json())
    assert len(copied_facts.json()) == 3
    source_message_ids = {
        message["id"]
        for message in client.get(
            f"/v1/projects/{project_id}/versions/1/messages"
        ).json()
    }
    copied_message_ids = {message["id"] for message in copied_messages.json()}
    assert source_message_ids.isdisjoint(copied_message_ids)
    assert all(
        set(fact["reference_message_ids"]) <= copied_message_ids
        for fact in copied_facts.json()
    )

    version_two_correction = _message(
        client,
        project_id,
        2,
        role="user",
        message_kind="correction",
        content="第二版另有新確認。",
    )
    updated = client.post(
        f"/v1/projects/{project_id}/versions/2/facts/{copied_facts.json()[0]['id']}/correct",
        json={
            "status": "confirmed",
            "value": "第二版服務營運",
            "correction_reason": "第二版修正",
            "reference_message_ids": [version_two_correction["id"]],
        },
    )
    assert updated.status_code == 200
    assert (
        client.get(f"/v1/projects/{project_id}/versions/1/facts").json()[0]["value"]
        == "服務營運"
    )

    client.close()
    reloaded = _client(tmp_path)
    assert reloaded.get(f"/v1/projects/{project_id}").status_code == 200
    assert len(reloaded.get(f"/v1/projects/{project_id}/versions").json()) == 2
    assert (
        len(reloaded.get(f"/v1/projects/{project_id}/versions/2/messages").json()) == 7
    )
    assert database_path.exists()


def test_project_history_api_requires_database_and_never_echoes_extra_input(
    tmp_path: Path,
) -> None:
    without_database = TestClient(
        create_app(chat_model=GenericFakeChatModel(messages=iter([])))
    )
    unavailable = without_database.post("/v1/projects", json={"project_name": "Safe"})
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "persistence_not_configured"

    client = _client(tmp_path)
    project = client.post("/v1/projects", json={"project_name": "Safe"}).json()
    response = client.post(
        f"/v1/projects/{project['project_id']}/versions/1/messages",
        json={
            "role": "user",
            "message_kind": "user_input",
            "content": "safe",
            "system_prompt": SENSITIVE_MARKER,
            "authorization": SENSITIVE_MARKER,
        },
    )

    assert response.status_code == 422
    assert SENSITIVE_MARKER not in response.text

    invalid_pair = client.post(
        f"/v1/projects/{project['project_id']}/versions/1/messages",
        json={
            "role": "user",
            "message_kind": "question",
            "content": "must not persist",
        },
    )
    assert invalid_pair.status_code == 409
    assert invalid_pair.json()["error"]["code"] == "invalid_visible_message"
    assert (
        client.get(f"/v1/projects/{project['project_id']}/versions/1/messages").json()
        == []
    )


def test_project_creation_keeps_only_safe_selected_model_snapshot(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    profile = client.post(
        "/v1/model-profiles",
        json={
            "profile_name": "Local Qwen",
            "base_url": "http://127.0.0.1:8080/v1",
            "model_name": "qwen-local",
            "api_key": SENSITIVE_MARKER,
        },
    ).json()
    client.post(f"/v1/model-profiles/{profile['id']}/select")

    created = client.post("/v1/projects", json={"project_name": "Snapshot"})

    assert created.status_code == 201
    assert created.json()["selected_model"] == {
        "profile_id": profile["id"],
        "profile_name": "Local Qwen",
        "model_name": "qwen-local",
    }
    assert SENSITIVE_MARKER not in created.text
    assert "base_url" not in created.text
